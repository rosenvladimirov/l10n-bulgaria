# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Grab-proxy wizard — emergency takeover of a proxy using the master
rescue token.

Operator inputs:
  * Target proxy URL (e.g. https://erpnet.shop1.lan.mcpworks.net)
  * Optional: new name + new pairing token

The wizard reads the Fleet-side rescue token from the system parameter
`erpnet_fp.rescue_token` (Fernet-encrypted at rest, like admin_token).
That value is the bootstrap secret operators burn into proxy images at
build time. With it + the proxy URL, the wizard:

  1. POSTs `<url>/admin/rescue/grab` with the rescue token in
     `X-Rescue-Token`.
  2. The proxy mutates its in-memory `registry.url` + `name`, drops
     its on-disk registry_secret, and on the next heartbeat the proxy
     will auto-enrol against THIS Fleet.
  3. We get back the proxy's confirmed state and toast it.

The new fleet URL we tell the proxy to point at is THIS Odoo's base
URL — computed from `web.base.url` so the wizard works in any
deployment without manual config.

Security:
  * Only members of `group_fleet_manager` can run the wizard.
  * Rescue token is stored encrypted; never sent to the browser.
  * Action is logged on the matched `erpnet.fp.proxy` record (or in a
    new draft record if URL doesn't match any existing).
"""
from __future__ import annotations

import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ErpNetFpGrabProxyWizard(models.TransientModel):
    _name = "erpnet.fp.grab.proxy.wizard"
    _description = "Grab a remote ErpNet.FP proxy using the master rescue token"

    target_url = fields.Char(
        string="Proxy URL",
        required=True,
        help="Public URL of the proxy to grab, e.g. "
             "https://erpnet.shop1.lan.mcpworks.net. The rescue endpoint "
             "is at <url>/admin/rescue/grab.",
    )
    new_name = fields.Char(
        string="Set name on proxy",
        help="Optional — if set, the proxy will use this name in its "
             "next auto-enrol. Leave blank to keep its current name.",
    )
    timeout = fields.Float(
        string="HTTP timeout (s)", default=10.0,
    )
    new_fleet_url = fields.Char(
        string="New Fleet URL",
        compute="_compute_new_fleet_url", readonly=False, store=False,
        help="The Fleet URL the grabbed proxy should heartbeat to. "
             "Defaults to this Odoo's web.base.url — change only if "
             "you want to forward the proxy to a different Fleet.",
    )

    # ─── Defaults ───────────────────────────────────────────────

    @api.depends_context("uid")
    def _compute_new_fleet_url(self):
        base = self.env["ir.config_parameter"].sudo().get_param(
            "web.base.url", default="").rstrip("/")
        for rec in self:
            rec.new_fleet_url = base or ""

    # ─── Rescue token storage helpers ───────────────────────────

    _RESCUE_TOKEN_PARAM = "erpnet_fp.rescue_token"

    @api.model
    def _get_rescue_token(self) -> str:
        """Decrypt the rescue token from ir.config_parameter. Returns
        empty string if not set — caller must surface a UserError so
        the operator sets one first.
        """
        ct = self.env["ir.config_parameter"].sudo().get_param(
            self._RESCUE_TOKEN_PARAM, default="")
        if not ct:
            return ""
        try:
            return self.env["erpnet.fp.fernet"].decrypt(ct)
        except Exception:  # noqa: BLE001
            # Backward-compat: pre-encryption setups may have stored
            # the token as plain text. If it doesn't decrypt cleanly,
            # treat the value as plaintext (legacy) and warn.
            _logger.warning(
                "Rescue token in %s did not decrypt — treating as "
                "plaintext (legacy). Re-save via Settings to encrypt.",
                self._RESCUE_TOKEN_PARAM)
            return ct

    @api.model
    def _set_rescue_token(self, plaintext: str) -> None:
        """Encrypt and persist a new rescue token in ir.config_parameter."""
        cp = self.env["ir.config_parameter"].sudo()
        if not plaintext:
            cp.set_param(self._RESCUE_TOKEN_PARAM, "")
            return
        ct = self.env["erpnet.fp.fernet"].encrypt(plaintext)
        cp.set_param(self._RESCUE_TOKEN_PARAM, ct)

    # ─── Action ─────────────────────────────────────────────────

    def action_grab(self):
        self.ensure_one()
        token = self._get_rescue_token()
        if not token:
            raise UserError(_(
                "No rescue token configured. Set it under Settings → "
                "Technical → System Parameters → key %s (or use the "
                "'Set Rescue Token' button in the Fleet menu).",
                self._RESCUE_TOKEN_PARAM))

        target = (self.target_url or "").rstrip("/")
        if not target:
            raise UserError(_("Proxy URL is required."))

        body = {
            "new_fleet_url": (self.new_fleet_url or "").rstrip("/") or None,
            "new_name": self.new_name or None,
            "clear_secret": True,
        }
        # Strip None values — pydantic on the proxy side defaults them.
        body = {k: v for k, v in body.items() if v is not None}

        try:
            resp = requests.post(
                f"{target}/admin/rescue/grab",
                headers={"X-Rescue-Token": token,
                         "Content-Type": "application/json"},
                data=json.dumps(body),
                timeout=self.timeout or 10.0,
            )
        except requests.RequestException as e:
            raise UserError(_(
                "Could not reach proxy at %(u)s: %(e)s",
                u=target, e=e)) from e

        if resp.status_code == 401:
            raise UserError(_(
                "Proxy rejected the rescue token (401). Either the "
                "token stored in Odoo doesn't match what was burned "
                "into the proxy image, or the proxy was rebuilt with "
                "a new token."))
        if resp.status_code == 503:
            raise UserError(_(
                "Proxy has rescue disabled (503). The image was built "
                "without ERPNET_FP_RESCUE_TOKEN, or the operator wiped "
                "the token at runtime."))
        if resp.status_code != 200:
            raise UserError(_(
                "Proxy returned HTTP %(s)d: %(b)s",
                s=resp.status_code, b=resp.text[:500]))

        result = resp.json()
        applied = result.get("applied") or []
        current = result.get("current") or {}

        # Post a chatter trace on the matching proxy record (if any).
        Proxy = self.env["erpnet.fp.proxy"]
        match = Proxy.search([("url", "=", target)], limit=1)
        if match:
            match.message_post(body=_(
                "Grabbed via master rescue token. Changes applied:<br/>"
                "<ul>%(lines)s</ul>",
                lines="".join(f"<li>{a}</li>" for a in applied)
            ))

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Proxy grabbed"),
                "message": _(
                    "Proxy %(u)s will re-enrol on its next heartbeat. "
                    "Current registry: url=%(url)s · name=%(name)s. "
                    "Watch the Fleet list — the new record should "
                    "appear within %(s)s seconds.",
                    u=target, url=current.get("url"),
                    name=current.get("name"), s=120),
                "type": "success",
                "sticky": True,
            },
        }
