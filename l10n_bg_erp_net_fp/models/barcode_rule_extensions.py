# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Extend `barcode.rule` with **N routing targets** (form+field) and
expose a JSON dump method on `barcode.nomenclature` for the Odoo
ErpNet.FP proxy to consume.

The proxy parses scans locally (without the round-trip to Odoo)
using this dump; each scan envelope it emits on bus_inject is
enriched with `data.target = [{model, field, form_xmlid}, ...]`
and `data.parsed_value`, so the browser handler can drive the
value into every matching open form simultaneously.
"""
import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DUMP_VERSION = 1


class BarcodeRule(models.Model):
    _inherit = "barcode.rule"

    l10n_bg_target_ids = fields.One2many(
        "l10n.bg.barcode.rule.target",
        "rule_id",
        string="Routing targets",
        help="Each scan matching this rule fills ALL listed (model, "
        "field, form) slots simultaneously. Add as many targets as "
        "you need — the browser handler skips ones whose form isn't "
        "currently open.",
    )
    l10n_bg_target_count = fields.Integer(
        compute="_compute_l10n_bg_target_count",
        store=False,
    )

    @api.depends("l10n_bg_target_ids")
    def _compute_l10n_bg_target_count(self):
        for r in self:
            r.l10n_bg_target_count = len(r.l10n_bg_target_ids)


class BarcodeNomenclature(models.Model):
    _inherit = "barcode.nomenclature"

    @api.model
    def parse_for_target(self, barcode):
        """Parse `barcode` and return the matched rule's routing
        targets, plus the parsed value. Multi-target — the caller
        is expected to fan out to all (model, field, form) slots
        listed in `target`.

        Returns:
            {
                rule_id, type, encoding, base_code, parsed_value,
                target: [{model, field, form_xmlid}, ...],
            }
            or None if no rule matches.
        """
        self.ensure_one()
        parsed = self.parse_barcode(barcode)
        if not parsed or parsed.get("type") == "error":
            return None
        rule = self.rule_ids.filtered(
            lambda r: r.type == parsed.get("type")
            and r.encoding == parsed.get("encoding")
        )[:1]
        targets = []
        if rule:
            for t in rule.l10n_bg_target_ids.filtered("active"):
                row = {
                    "model": t.model_id.model,
                    "field": t.field,
                }
                if t.form_xmlid:
                    row["form_xmlid"] = t.form_xmlid
                targets.append(row)
        return {
            "rule_id": rule.id if rule else False,
            "type": parsed.get("type"),
            "encoding": parsed.get("encoding"),
            "base_code": parsed.get("base_code") or parsed.get("code"),
            "parsed_value": parsed.get("value"),
            "target": targets,
        }

    # ─── proxy dump + push ────────────────────────────────────────

    @api.model
    def dump_for_proxy(self):
        """Serialise this nomenclature + every rule + every routing
        target into a JSON-friendly dict the proxy can persist and
        use for local parsing.

        Schema (versioned):

            {
                "version": 1,
                "nomenclature": {"id": int, "name": str,
                                 "upc_ean_conv": str},
                "rules": [
                    {
                        "id": int,
                        "name": str,
                        "type": str,
                        "encoding": str,
                        "pattern": str,
                        "sequence": int,
                        "targets": [
                            {"model": str, "field": str,
                             "form_xmlid": str|None,
                             "sequence": int},
                            ...
                        ],
                    },
                    ...
                ],
            }
        """
        self.ensure_one()
        rules = []
        for r in self.rule_ids.sorted("sequence"):
            targets = []
            for t in r.l10n_bg_target_ids.filtered("active").sorted("sequence"):
                targets.append({
                    "model": t.model_id.model,
                    "field": t.field,
                    "form_xmlid": t.form_xmlid or None,
                    "sequence": t.sequence,
                })
            rules.append({
                "id": r.id,
                "name": r.name,
                "type": r.type,
                "encoding": r.encoding,
                "pattern": r.pattern,
                "sequence": r.sequence,
                "targets": targets,
            })
        return {
            "version": DUMP_VERSION,
            "nomenclature": {
                "id": self.id,
                "name": self.name,
                "upc_ean_conv": self.upc_ean_conv,
            },
            "rules": rules,
        }

    def action_push_to_proxy_hosts(self):
        """Push the dump_for_proxy() payload to every active proxy-
        mode fiscal printer device's host via
        `POST /admin/nomenclature/reload`.

        Aggregates per-host results in a UserError-style summary if
        anything failed; otherwise returns a transient ir.actions
        notification. SSL verify is OFF on purpose — proxy hosts use
        Cloudflare Origin certs or self-signed in the merchant LAN.
        """
        self.ensure_one()
        payload = self.dump_for_proxy()
        hosts = self.env["fiscal.printer.device"].search([
            ("active", "=", True),
            ("connection_mode", "=", "proxy"),
            ("host", "!=", False),
        ]).mapped("host")
        # Dedupe — many devices may share a host
        hosts = sorted(set(h.rstrip("/") for h in hosts))
        if not hosts:
            raise UserError(_(
                "No active proxy-mode fiscal.printer.device found — "
                "nowhere to push the nomenclature to."))
        ok, errors = [], []
        for host in hosts:
            url = f"{host}/admin/nomenclature/reload"
            try:
                resp = requests.post(
                    url, json=payload, timeout=8.0, verify=False)
                if 200 <= resp.status_code < 300:
                    ok.append(host)
                else:
                    errors.append(f"{host}: HTTP {resp.status_code} "
                                  f"{resp.text[:200]}")
            except requests.RequestException as e:
                errors.append(f"{host}: {e}")
        if errors:
            raise UserError(_(
                "Push completed with errors:\n"
                "OK (%(ok)d): %(ok_list)s\n"
                "Failed (%(err)d):\n%(err_list)s"
            ) % {
                "ok": len(ok),
                "ok_list": ", ".join(ok) or "—",
                "err": len(errors),
                "err_list": "\n".join("  • " + e for e in errors),
            })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Nomenclature pushed"),
                "message": _("Pushed to %(n)d proxy host(s): %(list)s") % {
                    "n": len(ok), "list": ", ".join(ok),
                },
                "sticky": False,
            },
        }
