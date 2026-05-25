# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
pos.session — BlueCash signal push (Odoo → proxy → Android).

Implements the Odoo side of `anchor_bluecash_shift_signal_contract.md`:
when a `pos.session` opens or is asked to close, we POST a shift event
to each linked fiscal-device's proxy endpoint.

Independent of external-POS mode: any session with paired Android-side
fiscal devices (BlueCash PLU clients) receives signals — also useful
in mixed mode where BlueCash is one device alongside an Odoo POS UI.

Auth: HMAC-SHA256 over canonical body, secret =
`ir.config_parameter('iot_token')` — symmetric with shift_close.

This is best-effort: a network failure to the proxy does NOT block the
pos.session state change. The cashier can still open / close from the
UI. Failures are logged and a non-blocking warning is appended to
`session.message_post`.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


def _canonicalise(body: dict) -> bytes:
    return json.dumps(body, separators=(",", ":"),
                      sort_keys=True,
                      ensure_ascii=False).encode("utf-8")


def _sign(raw: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw,
                    hashlib.sha256).hexdigest()


class PosSession(models.Model):
    _inherit = "pos.session"

    # ─── Hooks ───────────────────────────────────────────────────────

    def action_pos_session_open(self):
        # Standard flow first; ние просто наблюдаваме.
        res = super().action_pos_session_open()
        for sess in self:
            try:
                sess._l10n_bg_emit_shift_signal("shift.open")
            except Exception:  # noqa: BLE001
                # Сигналът не трябва да блокира отварянето на сесията.
                _logger.exception(
                    "shift.open signal push failed for session #%s",
                    sess.id,
                )
        return res

    def action_pos_session_closing_control(self, *args, **kwargs):
        # Изпращаме `shift.close.request` ПРЕДИ да тръгне стандартния
        # control wizard — за да даде шанс на cashier-а да види
        # prompt-а в Android UI-то докато Odoo показва своя.
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
        """Push one signal event to each linked fiscal device's proxy.

        Discovery:
            session.config_id.l10n_bg_all_fiscal_devices
              → fiscal.printer.device records
              → device.host (proxy URL) + device.l10n_bg_device_serial

        Per device:
            POST <host>/devices/<serial>/events/push
                  X-Registry-Signature: <hmac>
            Body: {"event": {type, pos_session_id, operator_code,
                             fiscal_day_number, issued_at, reason}}

        Returns the number of devices the event was successfully
        delivered to.
        """
        self.ensure_one()
        secret = self.env["ir.config_parameter"].sudo().get_param(
            "iot_token") or ""
        secret = secret.strip("\n").strip()
        if not secret:
            _logger.info(
                "shift signal %s: skipped — iot_token ICP empty", kind)
            return 0
        # Devices may be configured on l10n_bg_all_fiscal_devices (a
        # computed superset на различни релации) или по-просто чрез
        # config_id.fiscal_printer_device_ids. Първо проверяваме
        # подходящия атрибут — двата съществуват в текущия модул.
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
        # Build event payload.
        operator_code = ""
        if self.user_id:
            # Cashier code (cashier.id или login може да се ползва;
            # за съвместимост с BlueCash side който очаква numeric code
            # на operator) — fallback на user-id.
            operator_code = str(self.user_id.id)
        # Fiscal day number — ако имаме linked fiscal session, ползваме
        # неговия Z-cycle counter; иначе празно (BlueCash ще ползва
        # своя локален counter).
        fiscal_day = 0
        if hasattr(self, "l10n_bg_fiscal_session_id"):
            fs = self.l10n_bg_fiscal_session_id
            if fs:
                fiscal_day = int(
                    getattr(fs, "fiscal_day_number", 0) or 0)
        event_base = {
            "type": kind,
            "pos_session_id": self.id,
            "operator_code": operator_code,
            "fiscal_day_number": fiscal_day,
            "issued_at": fields.Datetime.now().isoformat() + "Z",
        }
        if reason:
            event_base["reason"] = reason

        delivered = 0
        for dev in devices:
            host = (getattr(dev, "host", "") or "").strip().rstrip("/")
            serial = (getattr(dev, "l10n_bg_device_serial", "")
                      or "").strip()
            if not host or not serial:
                continue
            body = {"event": dict(event_base)}
            raw = _canonicalise(body)
            sig = _sign(raw, secret)
            url = f"{host}/devices/{serial}/events/push"
            req = urlrequest.Request(
                url, data=raw, method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-Registry-Signature": sig,
                },
            )
            try:
                # NOTE: synchronous HTTP in an Odoo model is OK only
                # because this is a one-shot fire-and-forget per device.
                # Timeout е кратък (3 s) за да не блокираме UI-то ако
                # proxy-то не отговаря.
                # SSL: устройствата обикновено са LAN със self-signed
                # сертификат — за production обмислете proper trust.
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urlrequest.urlopen(req, timeout=3.0,
                                        context=ctx) as resp:
                    if 200 <= resp.status < 300:
                        delivered += 1
                    else:
                        _logger.warning(
                            "shift signal %s to %s: HTTP %s",
                            kind, url, resp.status)
            except HTTPError as exc:
                _logger.warning(
                    "shift signal %s to %s: HTTP %s — %s",
                    kind, url, exc.code, exc.reason)
            except URLError as exc:
                _logger.info(
                    "shift signal %s to %s unreachable: %s",
                    kind, url, exc.reason)
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "shift signal %s to %s failed", kind, url)
        if delivered:
            _logger.info(
                "shift signal %s: delivered to %d device(s) on "
                "session #%s", kind, delivered, self.id)
        return delivered
