# Copyright 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import requests

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)

DEFAULT_KICKBOX_URL = (
    "https://raw.githubusercontent.com/disposable-email-domains/"
    "disposable-email-domains/master/disposable_email_blocklist.conf"
)
HTTP_TIMEOUT = 30


class DisposableEmailDomain(models.Model):
    _name = "disposable.email.domain"
    _description = "Disposable Email Domain Blocklist"
    _order = "name"

    name = fields.Char(
        string="Domain",
        required=True,
        index=True,
        help="Lower-cased domain name (e.g. mailinator.com).",
    )
    source = fields.Selection(
        [
            ("seed", "Seed (shipped)"),
            ("kickbox", "Kickbox upstream"),
            ("package", "Python package"),
            ("manual", "Manual"),
        ],
        default="manual",
        required=True,
    )
    active = fields.Boolean(default=True)
    last_seen_upstream = fields.Datetime(
        string="Last Seen Upstream",
        help="Last time this domain was confirmed in the upstream Kickbox "
             "list. Empty means manually entered or shipped seed.",
    )

    _sql_constraints = [
        ("name_unique", "UNIQUE(name)", "Disposable domain must be unique."),
    ]

    # ── ormcache for hot-path lookups ──────────────────────────────────────

    @tools.ormcache()
    def _active_domain_set(self):
        """Cached frozenset of active disposable domains for O(1) lookup.

        Invalidated automatically by overrides of create/write/unlink below.
        """
        return frozenset(
            self.with_context(active_test=True)
            .search([("active", "=", True)])
            .mapped("name")
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name"):
                vals["name"] = vals["name"].strip().lower()
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        if "name" in vals and vals["name"]:
            vals["name"] = vals["name"].strip().lower()
        result = super().write(vals)
        if {"name", "active"} & set(vals.keys()):
            self.env.registry.clear_cache()
        return result

    def unlink(self):
        result = super().unlink()
        self.env.registry.clear_cache()
        return result

    # ── disposability check ────────────────────────────────────────────────

    @api.model
    def _is_disposable(self, email):
        """Return True if the domain (or any parent suffix) is in the active
        blocklist.

        Handles:
        * Plus addressing (`foo+spam@bar.com`) — only the domain part is checked.
        * Subdomain attacks (`foo@x.mailinator.com`) — every dot-suffix is tried.
        * Punycode IDN — the domain is converted to ASCII before lookup.
        """
        if not email or "@" not in email:
            return False
        domain = email.rsplit("@", 1)[1].strip().lower()
        if not domain:
            return False
        try:
            domain = domain.encode("idna").decode("ascii")
        except (UnicodeError, UnicodeDecodeError):
            # Already ASCII or malformed — fall back to as-is.
            pass

        blocked = self._active_domain_set()
        if domain in blocked:
            return True
        # Check parent suffixes: foo.bar.mailinator.com → bar.mailinator.com
        # → mailinator.com.
        parts = domain.split(".")
        for i in range(1, len(parts) - 1):
            suffix = ".".join(parts[i:])
            if suffix in blocked:
                return True
        return False

    # ── upstream refresh helpers ───────────────────────────────────────────

    @api.model
    def _refresh_from_kickbox(self, url=None):
        """Fetch the upstream list, INSERT new domains, mark missing as
        inactive (preserving audit trail rather than deleting).

        Returns dict ``{added: int, deactivated: int}``.
        """
        if not url:
            url = self.env["ir.config_parameter"].sudo().get_param(
                "website_sale_email_verification.disposable_url",
                DEFAULT_KICKBOX_URL,
            )
        try:
            response = requests.get(url, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as exc:
            _logger.warning("Disposable blocklist refresh failed: %s", exc)
            raise

        upstream = {
            line.strip().lower()
            for line in response.text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        existing = {d.name: d for d in self.with_context(active_test=False).search([])}

        now = fields.Datetime.now()
        added = 0
        for domain in upstream:
            rec = existing.get(domain)
            if rec is None:
                self.create({
                    "name": domain,
                    "source": "kickbox",
                    "active": True,
                    "last_seen_upstream": now,
                })
                added += 1
            else:
                rec.write({
                    "active": True,
                    "last_seen_upstream": now,
                    # Promote to kickbox source if it was previously seen only
                    # as a seed/manual entry.
                    "source": (
                        "kickbox"
                        if rec.source in ("seed", "manual")
                        else rec.source
                    ),
                })

        # Deactivate domains that were previously sourced from kickbox/package
        # but no longer appear upstream. Leave seed/manual entries alone.
        deactivated = 0
        for name, rec in existing.items():
            if name in upstream:
                continue
            if rec.source in ("kickbox", "package") and rec.active:
                rec.active = False
                deactivated += 1

        _logger.info(
            "Disposable blocklist refreshed from upstream: +%s new, "
            "%s deactivated.",
            added,
            deactivated,
        )
        return {"added": added, "deactivated": deactivated}

    @api.model
    def _refresh_from_package(self):
        """Fallback: load from the ``disposable_email_domains`` Python package
        when the upstream URL is unreachable.
        """
        try:
            import disposable_email_domains as ded
        except ImportError:
            _logger.warning(
                "disposable_email_domains package not installed — cannot "
                "fall back to it. Install with: pip install "
                "disposable_email_domains",
            )
            return {"added": 0}

        domains = {d.lower() for d in ded.blocklist}
        existing = set(
            self.with_context(active_test=False)
            .search([])
            .mapped("name")
        )
        new_domains = domains - existing
        if not new_domains:
            return {"added": 0}
        self.create([
            {"name": d, "source": "package", "active": True}
            for d in sorted(new_domains)
        ])
        _logger.info(
            "Disposable blocklist seeded from package: +%s new entries.",
            len(new_domains),
        )
        return {"added": len(new_domains)}

    @api.model
    def _cron_refresh_blocklist(self):
        """Cron entry point. Try Kickbox first; fall back to the Python
        package on network error.
        """
        try:
            return self._refresh_from_kickbox()
        except Exception:
            _logger.exception(
                "Kickbox refresh failed, falling back to "
                "disposable_email_domains package.",
            )
            return self._refresh_from_package()

    @api.model
    def action_refresh_now(self):
        """Bound to a button on the settings form."""
        result = self._cron_refresh_blocklist()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": "Blocklist refreshed",
                "message": "Added %s, deactivated %s domains."
                           % (result.get("added", 0), result.get("deactivated", 0)),
                "sticky": False,
            },
        }
