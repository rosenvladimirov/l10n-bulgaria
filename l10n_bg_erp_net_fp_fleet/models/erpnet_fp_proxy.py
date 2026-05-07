# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
ErpNet.FP proxy registry model.

Each record represents one ErpNet.FP proxy instance (one per shop
typically). The pairing flow is:

  1. Admin clicks "Generate Pairing Token" on a draft proxy → an
     opaque token + 1 h expiry are written to the record.
  2. Admin pastes the token into the proxy's `config.yaml`
     (`server.registry.pairing_token`) and starts the proxy.
  3. Proxy POSTs `/erp_net_fp/registry/pair` with the token; the
     controller validates + consumes it, generates a long-lived
     `registry_secret`, returns it. From that moment on, the proxy
     heartbeats with HMAC-signed bodies.

The admin_token (which lets us call the proxy's `/admin/*` endpoints)
is stored Fernet-encrypted; only :py:meth:`get_admin_token` decrypts
it on demand.
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Time window to use a freshly-generated pairing token. Short enough
# to limit blast radius if it leaks, long enough to copy-paste it
# into a remote proxy config.
_PAIRING_TTL = timedelta(hours=1)

# Tolerance for "alive" computation — heartbeat interval is 60 s by
# default, so 3× = 180 s gives one missed beat before going red.
_ALIVE_WINDOW_SECONDS = 180


class ErpNetFpProxy(models.Model):
    _name = "erpnet.fp.proxy"
    _description = "ErpNet.FP Proxy Instance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"
    _rec_name = "name"

    # ─── Identity ───────────────────────────────────────────────

    name = fields.Char(
        required=True, tracking=True,
        help="Human-readable identifier — e.g. 'sofia-shop-1'.",
    )
    url = fields.Char(
        string="Proxy URL",
        help="Public URL where this proxy is reachable, e.g. "
             "https://erpnet.shop1.lan.mcpworks.net. Used for "
             "back-channel /admin/* calls (Update / Logs / VAT).",
    )
    host = fields.Char(
        readonly=True, tracking=True,
        help="Hostname reported by the proxy in its last heartbeat.",
    )
    version = fields.Char(
        readonly=True, tracking=True,
        help="Proxy semver, reported in heartbeat.",
    )
    notes = fields.Text()

    # ─── Pairing ────────────────────────────────────────────────

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("pairing", "Pairing pending"),
            ("active", "Active"),
            ("archived", "Archived"),
        ],
        default="draft", tracking=True, required=True,
    )
    pairing_token = fields.Char(
        readonly=True, copy=False, groups="base.group_system",
        help="One-time token; valid for one hour. Paste into the proxy's "
             "config.yaml under server.registry.pairing_token, then start "
             "the proxy. Cleared after first successful pair.",
    )
    pairing_expires = fields.Datetime(
        readonly=True, copy=False, groups="base.group_system",
    )
    registry_secret = fields.Char(
        readonly=True, copy=False, groups="base.group_system",
        help="Long-lived shared secret used by the proxy to HMAC-sign "
             "heartbeat bodies. Generated automatically on pair.",
    )

    # ─── Heartbeat state ────────────────────────────────────────

    last_seen = fields.Datetime(
        readonly=True, tracking=False,
        help="Timestamp of the last accepted heartbeat.",
    )
    alive = fields.Boolean(
        compute="_compute_alive", store=False,
        help="True if last_seen is within "
             f"{_ALIVE_WINDOW_SECONDS} s.",
    )
    devices_json = fields.Text(
        readonly=True,
        help="JSON: {printers: [...], pinpads: [...], scales: [...], "
             "readers: [...], displays: [...]}",
    )
    devices_summary = fields.Char(
        compute="_compute_devices_summary", store=False,
    )

    # ─── Admin token (Fernet-encrypted at rest) ─────────────────

    admin_token_encrypted = fields.Char(
        readonly=True, copy=False, groups="base.group_system",
        help="Fernet ciphertext of the proxy's admin token. Reported "
             "by the proxy in its heartbeat so this backend can call "
             "/admin/* endpoints (self-update, logs, vat-rates).",
    )
    has_admin_token = fields.Boolean(
        compute="_compute_has_admin_token", store=False,
    )

    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)",
         "Another proxy already uses this name."),
    ]

    # ─── Computes ───────────────────────────────────────────────

    @api.depends("last_seen")
    def _compute_alive(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.last_seen:
                rec.alive = False
                continue
            delta = (now - rec.last_seen).total_seconds()
            rec.alive = delta < _ALIVE_WINDOW_SECONDS

    @api.depends("devices_json")
    def _compute_devices_summary(self):
        for rec in self:
            if not rec.devices_json:
                rec.devices_summary = ""
                continue
            try:
                d = json.loads(rec.devices_json)
            except (ValueError, TypeError):
                rec.devices_summary = "?"
                continue
            parts = []
            for k in ("printers", "pinpads", "scales", "readers", "displays"):
                lst = d.get(k) or []
                if lst:
                    parts.append(f"{k[:1].upper()}{len(lst)}")
            rec.devices_summary = " ".join(parts) or "—"

    @api.depends("admin_token_encrypted")
    def _compute_has_admin_token(self):
        for rec in self.sudo():
            rec.has_admin_token = bool(rec.admin_token_encrypted)

    # ─── Admin token helpers ────────────────────────────────────

    def get_admin_token(self) -> str:
        """Decrypt and return the stored admin token. Returns '' if
        none was reported yet. Always callable through `sudo()` —
        ACL on the field already prevents leakage to non-system
        users via XML-RPC.
        """
        self.ensure_one()
        ct = self.sudo().admin_token_encrypted or ""
        if not ct:
            return ""
        return self.env["erpnet.fp.fernet"].decrypt(ct)

    def set_admin_token(self, plaintext: str) -> None:
        """Encrypt and persist a new admin token. Called from the
        registry controller on every heartbeat (the proxy's token
        can rotate without user action — e.g. after a reset)."""
        self.ensure_one()
        if not plaintext:
            self.sudo().admin_token_encrypted = ""
            return
        ct = self.env["erpnet.fp.fernet"].encrypt(plaintext)
        self.sudo().admin_token_encrypted = ct

    # ─── Pairing actions ────────────────────────────────────────

    def action_generate_pairing_token(self):
        """Generate a fresh single-use pairing token + 1 h expiry.

        Resetting an already-active proxy's pairing token does NOT
        invalidate the existing registry_secret — the operator must
        also clear it (button "Reset secret") if they want to truly
        re-pair from scratch.
        """
        for rec in self:
            token = secrets.token_urlsafe(32)
            rec.sudo().write({
                "pairing_token": token,
                "pairing_expires": fields.Datetime.now() + _PAIRING_TTL,
                "state": "pairing" if rec.state == "draft" else rec.state,
            })
            rec.message_post(
                body=_("Pairing token generated; expires in %(h)s hour(s).",
                       h=_PAIRING_TTL.total_seconds() // 3600),
            )
        return self._show_pairing_dialog()

    def action_reset_secret(self):
        """Forget the registry_secret + admin_token. Forces the proxy
        to re-pair on next start. Use when a secret leaks or the
        proxy is being moved to a different shop."""
        for rec in self:
            rec.sudo().write({
                "registry_secret": False,
                "admin_token_encrypted": False,
                "last_seen": False,
                "version": False,
                "host": False,
                "devices_json": False,
                "state": "draft",
            })
            rec.message_post(body=_("Registry secret reset — proxy must re-pair."))

    def action_archive_proxy(self):
        for rec in self:
            rec.state = "archived"

    def action_unarchive_proxy(self):
        for rec in self:
            rec.state = "draft"

    def _show_pairing_dialog(self):
        """Return a `display_notification` action so the user sees the
        token without having to navigate to a hidden field."""
        self.ensure_one()
        token = self.sudo().pairing_token or ""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Pairing token"),
                "message": _(
                    "Paste this into the proxy's config.yaml "
                    "under `server.registry.pairing_token`:\n\n%(t)s",
                    t=token,
                ),
                "type": "info",
                "sticky": True,
            },
        }

    # ─── Back-channel /admin/* buttons ──────────────────────────

    def _admin_call(self, method: str, path: str,
                    params: dict | None = None,
                    json_body: dict | None = None,
                    timeout: int = 30):
        """Wrapper for back-channel calls to the proxy's /admin/*."""
        import requests
        self.ensure_one()
        if not self.url:
            raise UserError(_(
                "Proxy URL is empty. Set it on the form before calling "
                "/admin/* endpoints."))
        token = self.get_admin_token()
        if not token:
            raise UserError(_(
                "No admin token recorded for this proxy. Wait for the "
                "next heartbeat or check that the proxy has bootstrapped "
                "its admin token (logs: ADMIN_TOKEN_BOOTSTRAP banner)."))
        url = self.url.rstrip("/") + path
        try:
            r = requests.request(
                method, url,
                params=params,
                json=json_body,
                headers={"X-Admin-Token": token},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise UserError(_(
                "Cannot reach proxy at %(url)s: %(err)s",
                url=url, err=exc,
            )) from exc
        if r.status_code >= 400:
            raise UserError(_(
                "Proxy %(url)s returned %(code)s: %(body)s",
                url=url, code=r.status_code, body=r.text[:500],
            ))
        try:
            return r.json()
        except ValueError:
            return {"raw": r.text}

    def action_self_update(self):
        self.ensure_one()
        result = self._admin_call("POST", "/admin/self-update")
        msg = result.get("message") or _("Update scheduled.")
        self.message_post(body=_("Self-update triggered: %(m)s", m=msg))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Self-update scheduled"),
                "message": msg,
                "type": "success",
                "sticky": False,
            },
        }

    def action_view_logs(self):
        self.ensure_one()
        result = self._admin_call("GET", "/admin/logs",
                                  params={"tail": 200})
        lines = result.get("lines") or []
        text = "\n".join(
            f"{l.get('level','')[:4]:4s} {l.get('name','')}: {l.get('msg','')}"
            for l in lines[-200:]
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Last 200 log lines"),
                "message": text or _("(empty)"),
                "type": "info",
                "sticky": True,
            },
        }

    def action_open_program_vat_wizard(self):
        self.ensure_one()
        return {
            "name": _("Program VAT rates"),
            "type": "ir.actions.act_window",
            "res_model": "erpnet.fp.program.vat.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_proxy_id": self.id},
        }

    # ─── Cron: pairing-token expiry sweep ───────────────────────

    @api.model
    def _cron_expire_pairing_tokens(self):
        """Wipe expired pairing tokens so they can't be replayed."""
        now = fields.Datetime.now()
        expired = self.search([
            ("pairing_token", "!=", False),
            ("pairing_expires", "<", now),
        ])
        if expired:
            expired.sudo().write({
                "pairing_token": False,
                "pairing_expires": False,
            })
            _logger.info("Wiped %d expired pairing token(s)", len(expired))
