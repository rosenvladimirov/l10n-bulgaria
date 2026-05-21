# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Polimex controller part — a single function on a controller's I/O.

For the Odoo operator, the access controller breaks into discrete
parts: magnet/strike on output #1, motor on output #2, reader on
input #3, etc. Each row here is one such function.

Output parts (magnet/strike/motor) become access entries in the
proxy's access.yaml — they're things the controller can ACTUATE.

Input parts (reader/sensor/button) are documentation only; the
controller reports their state through F5/B3 event commands, and the
proxy decides what to do with them based on Odoo policy.
"""
from __future__ import annotations

import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


_KIND_SELECTION = [
    ("magnet", "Electromagnetic lock"),
    ("strike", "Electric strike"),
    ("motor", "Gate motor"),
    ("reader", "RFID / keypad reader"),
    ("sensor", "Door / motion sensor"),
    ("button", "Exit button / REX"),
]

# Sub-set that emits a proxy access entry — outputs the controller
# can ACTUATE. Inputs are observed, not written.
_OUTPUT_KINDS = ("magnet", "strike", "motor")


class PolimexPart(models.Model):
    _name = "polimex.part"
    _description = "Polimex Controller Part (one I/O function)"
    _order = "controller_id, sequence, io_channel, kind"
    _rec_name = "display_name"

    controller_id = fields.Many2one(
        "polimex.controller", required=True, ondelete="cascade",
        index=True,
    )
    name = fields.Char(
        required=True,
        help="Operator label — 'Front gate magnet', 'Lobby reader', etc.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    kind = fields.Selection(
        _KIND_SELECTION, required=True, default="magnet",
        help="What this part does. Outputs (magnet/strike/motor) become "
             "access.yaml entries; inputs (reader/sensor/button) are "
             "documentation only — the proxy observes them through the "
             "controller's event stream.",
    )
    io_channel = fields.Integer(
        string="I/O Channel",
        default=1, required=True,
        help="Output number on the controller (1..N depending on mode), "
             "or input number for sensor/reader/button.",
    )
    access_id = fields.Char(
        string="Access ID",
        help="Stable id used in the proxy's access.yaml. Defaults to "
             "`name` if empty. Must be unique across the whole proxy "
             "(not just this controller).",
    )
    notes = fields.Text()

    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("kind", "io_channel", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.kind or '?'}#{rec.io_channel or '?'} · {rec.name or ''}"
            ).strip(" ·")

    @api.depends("kind")
    def _compute_is_output(self):
        for rec in self:
            rec.is_output = rec.kind in _OUTPUT_KINDS

    is_output = fields.Boolean(compute="_compute_is_output", store=False)

    # ─── Operator actions ──────────────────────────────────────
    #
    # Output parts (magnet/strike/motor) get Open + Deny buttons that
    # POST against the owning proxy's REST surface synchronously.
    # The bus_inject side-effect (door.opened / door.denied) is emitted
    # by the proxy itself — operators see the toast within ~1s.

    def _call_proxy_access(self, action, seconds=None):
        """POST <proxy.url>/access/<access_id>/<action> with the proxy's
        admin_token. Returns the parsed JSON response. Raises UserError
        on transport/HTTP failures so the operator gets a clear message.
        """
        self.ensure_one()
        if not self.is_output:
            raise UserError(_(
                "Part %(p)s is kind '%(k)s' — only output parts "
                "(magnet/strike/motor) can be opened/denied.",
                p=self.display_name, k=self.kind))
        ctrl = self.controller_id
        if not ctrl.proxy_id:
            raise UserError(_("Controller %s has no proxy assigned.",
                              ctrl.name))
        proxy = ctrl.proxy_id
        base = (proxy.url or "").rstrip("/")
        if not base:
            raise UserError(_(
                "Proxy %s has no URL set — cannot reach its /access "
                "endpoint.", proxy.name))
        token = proxy.sudo().get_admin_token() if hasattr(
            proxy, "get_admin_token") else ""
        if not token:
            raise UserError(_(
                "Proxy %s hasn't reported an admin token yet (no "
                "heartbeat carrying it has arrived). Wait one minute "
                "after the proxy boots before trying again.",
                proxy.name))
        target_id = self.access_id or self.name
        url = f"{base}/access/{target_id}/{action}"
        body = {}
        if action == "open" and seconds is not None:
            body["seconds"] = float(seconds)
        try:
            r = requests.post(url, json=body,
                              headers={"X-Admin-Token": token},
                              timeout=8.0)
        except requests.RequestException as e:
            raise UserError(_(
                "Could not reach proxy at %(u)s: %(e)s",
                u=base, e=e)) from e
        if r.status_code != 200:
            raise UserError(_(
                "Proxy returned HTTP %(s)d: %(b)s",
                s=r.status_code, b=r.text[:400]))
        try:
            return r.json()
        except ValueError:
            return {"raw": r.text}

    def action_open(self):
        self.ensure_one()
        # Inherit controller's default pulse_seconds — None ⇒ proxy
        # uses its own default. Operators who want a non-default
        # duration can override here later if we add a wizard.
        secs = self.controller_id.pulse_seconds or None
        res = self._call_proxy_access("open", seconds=secs)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("🔓 Open"),
                "message": _("Proxy: %s", res.get("detail") or "ok"),
                "type": "success" if res.get("ok", True) else "danger",
                "sticky": False,
            },
        }

    def action_deny(self):
        self.ensure_one()
        res = self._call_proxy_access("deny")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("🔒 Deny"),
                "message": _("Proxy: %s", res.get("detail") or "ok"),
                "type": "warning" if res.get("ok", True) else "danger",
                "sticky": False,
            },
        }
