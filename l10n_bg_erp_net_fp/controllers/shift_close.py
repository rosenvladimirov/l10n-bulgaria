# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
BlueCash shift-close receiver.

Endpoint:
    POST /erp_net_fp/shift_close
    POST /erp_net_fp/shift_close/dry_run

Auth:
    X-Registry-Signature: HMAC-SHA256(raw_body, shared_secret) hex
    where `shared_secret = ir.config_parameter("iot_token")` — същият
    параметър, който iot_oca controller-а ползва при регистрация на
    устройствата. Симетрия с proxy `cfg.iot_setup.token`.

Body:
    Шаблонът от `anchor_bluecash_shift_sync_contract.md` §Android
    payload. Полета: device_serial, odoo_session_id, fiscal_day_number,
    operator_code, opened_at, closed_at, z_report_number, z_report_at,
    totals{}, receipts[], cash_movements[].

Behaviour:
    1. Verify HMAC.
    2. Delegate to `l10n.bg.erp.net.fp.shift.sync.apply(payload, dry_run)`.
    3. Return JSON response per contract:
       {status, odoo_session_id, odoo_orders_created,
        odoo_refunds_created, warnings: []}

Idempotency:
    Service layer dedupe by `(device_serial, fiscal_day_number,
    z_report_number)` + per-receipt UNS lookup. Re-POST returns same
    response without creating duplicate rows.

`type='http'` (not `type='json'`):
    Need raw body bytes for HMAC verification — `type='json'` would
    re-serialize and break the signature.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


def _json_response(payload: dict, status: int = 200) -> Response:
    return Response(
        json.dumps(payload, ensure_ascii=False),
        status=status,
        content_type="application/json; charset=utf-8",
    )


def _verify_hmac(body: bytes, secret: str, provided_sig: str) -> bool:
    """Const-time HMAC-SHA256 verify."""
    if not secret or not provided_sig:
        return False
    expected = hmac.new(secret.encode("utf-8"), body,
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_sig)


def _get_shared_secret(env) -> str:
    """Връща глобалния shared secret за shift_close auth.

    Симетрия с iot_oca: ползваме `iot_token` ICP (същият, който се
    задава при iot setup-а). Не въвеждаме нов ICP за да не плодим
    параметри — един shared secret per Odoo tenant.
    """
    ICP = env["ir.config_parameter"].sudo()
    return (ICP.get_param("iot_token") or "").strip("\n").strip()


class L10nBgFpShiftCloseController(http.Controller):

    @http.route(
        "/erp_net_fp/shift_close",
        type="http", auth="public", methods=["POST"], csrf=False,
        save_session=False,
    )
    def shift_close(self, **_kw):
        """Приема closed-shift payload от paired proxy."""
        return self._handle(dry_run=False)

    @http.route(
        "/erp_net_fp/shift_close/dry_run",
        type="http", auth="public", methods=["POST"], csrf=False,
        save_session=False,
    )
    def shift_close_dry_run(self, **_kw):
        """Същият payload, но връща planned diff без записи."""
        return self._handle(dry_run=True)

    def _handle(self, dry_run: bool) -> Response:
        body = request.httprequest.get_data() or b""
        sig = (request.httprequest.headers.get("X-Registry-Signature")
               or "").strip()
        if not sig:
            return _json_response(
                {"error": "X-Registry-Signature header missing"}, 401)
        secret = _get_shared_secret(request.env)
        if not secret:
            _logger.error(
                "shift_close: shared secret not configured "
                "(ir.config_parameter 'iot_token' empty)")
            return _json_response(
                {"error": "Server-side shared secret not configured"},
                503)
        if not _verify_hmac(body, secret, sig):
            _logger.warning("shift_close: HMAC mismatch")
            return _json_response(
                {"error": "X-Registry-Signature mismatch"}, 401)
        try:
            payload = json.loads(body or b"{}")
        except ValueError as exc:
            return _json_response(
                {"error": f"Invalid JSON body: {exc}"}, 400)

        Service = (request.env["l10n.bg.erp.net.fp.shift.sync"]
                   .sudo().with_context(active_test=False))
        try:
            result = Service.apply(payload, dry_run=dry_run)
        except ValueError as exc:
            # Структурни/бизнес валидационни грешки → 400
            _logger.info("shift_close validation error: %s", exc)
            return _json_response(
                {"error": str(exc), "status": "error"}, 400)
        except Exception:  # noqa: BLE001
            _logger.exception("shift_close handler failed")
            return _json_response(
                {"error": "Internal server error",
                 "status": "error"}, 500)
        # Service decides HTTP-code чрез special `_http_status` ключ
        # ако трябва (default 200; 409 при session conflict).
        http_status = int(result.pop("_http_status", 200))
        return _json_response(result, http_status)
