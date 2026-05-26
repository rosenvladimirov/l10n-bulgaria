# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""pos.session → BlueCash signal push (Odoo → proxy → Android).

Hooks the standard `pos.session` state transitions and delegates the
push to `l10n.bg.erp.net.fp.shift.bridge.client.emit_signal()`. The
client wraps a signed POST to `<host>/shifts/<serial>/signal`; the
proxy forwards over the persistent NDJSON TCP connection to Android.

Previous implementation (pre-15.10) ползваше urllib директно за POST
към `/devices/<serial>/events/push` + WS/SSE fan-out на проксито —
deprecated as part на shift bridge unification.

Independent of external-POS mode: any session с paired Android-side
fiscal devices receives signals. Best-effort: failures are logged
but never block the state transition.
"""
from __future__ import annotations

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = "pos.session"

    # ─── Hooks ───────────────────────────────────────────────────────

    def action_pos_session_open(self):
        res = super().action_pos_session_open()
        for sess in self:
            try:
                sess._l10n_bg_emit_shift_signal("shift.open")
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "shift.open signal push failed for session #%s",
                    sess.id,
                )
        return res

    def action_pos_session_closing_control(self, *args, **kwargs):
        # Изпращаме сигнала ПРЕДИ control wizard-а — Android да покаже
        # своя Z-prompt паралелно с Odoo UI-то.
        for sess in self:
            try:
                sess._l10n_bg_emit_shift_signal(
                    "shift.close.request", reason="operator")
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "shift.close.request signal push failed for "
                    "session #%s", sess.id,
                )
        return super().action_pos_session_closing_control(*args, **kwargs)

    # ─── Emitter ─────────────────────────────────────────────────────

    def _l10n_bg_emit_shift_signal(self, kind: str, reason: str = ""):
        """Push one signal event to each paired fiscal device.

        Device discovery остава непроменено: `config.l10n_bg_all_fiscal_devices`
        (computed superset) → fallback на `config.fiscal_printer_device_ids`.
        За всяко device викаме `bridge.client.emit_signal(...)`.
        """
        self.ensure_one()
        cfg = self.config_id
        devices = (
            getattr(cfg, "l10n_bg_all_fiscal_devices", False)
            or getattr(cfg, "fiscal_printer_device_ids", False)
            or self.env["fiscal.printer.device"]
        )
        if not devices:
            _logger.info(
                "shift signal %s: no fiscal devices on config %r",
                kind, cfg.display_name)
            return 0
        operator_code = ""
        if self.user_id:
            operator_code = str(self.user_id.id)
        fiscal_day = 0
        if hasattr(self, "l10n_bg_fiscal_session_id"):
            fs = self.l10n_bg_fiscal_session_id
            if fs:
                fiscal_day = int(
                    getattr(fs, "fiscal_day_number", 0) or 0)
        payload = {
            "pos_session_id": self.id,
            "operator_code": operator_code,
            "fiscal_day_number": fiscal_day,
            "issued_at": fields.Datetime.now().isoformat() + "Z",
        }
        if reason:
            payload["reason"] = reason

        Client = self.env["l10n.bg.erp.net.fp.shift.bridge.client"].sudo()
        delivered = 0
        for dev in devices:
            host = (getattr(dev, "host", "") or "").strip()
            serial = (getattr(dev, "l10n_bg_device_serial", "")
                      or "").strip()
            if not host or not serial:
                continue
            result = Client.emit_signal(dev, kind, payload)
            if result.get("ok"):
                delivered += 1
            elif result.get("error"):
                _logger.info(
                    "shift signal %s → %s: %s",
                    kind, dev.display_name, result["error"])
        if delivered:
            _logger.info(
                "shift signal %s: delivered to %d device(s) on "
                "session #%s", kind, delivered, self.id)
        return delivered
