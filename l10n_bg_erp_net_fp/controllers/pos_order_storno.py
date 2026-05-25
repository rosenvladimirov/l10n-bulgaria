# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
BlueCash storno Phase 2 — pos.order fiscal lookup + refund-printed sink.

Implements the Odoo side of `anchor_bluecash_storno_phase2_contract.md`:

  GET  /erp_net_fp/pos_order/<id>/fiscal_receipt
       Returns the lookup payload Android StornoRunner needs (UNS,
       doc_number, issued_at, device_serial, till_number, lines[],
       payments[]).

  GET  /erp_net_fp/pos_order/by_uns/<uns>/fiscal_receipt
       Cross-device variant — lookup by UNS instead of Odoo ID.

  POST /erp_net_fp/pos_order/<id>/refund_printed
       Android notifies after the storno is printed; we create a
       linked refund pos.order and store the storno UNS on it.

Auth: HMAC-SHA256 X-Registry-Signature, same as shift_close.
  * GET endpoints — signature over the URL path bytes (no leading slash).
  * POST endpoint — signature over the raw JSON body bytes.

Status flow:
  pos.order.state ∈ {paid, done}     → 200 OK, return lookup payload
  pos.order.state == invoiced        → 200 OK (refund still allowed)
  pos.order missing                  → 404 Not Found
  existing refund linked && covers   → 409 Conflict, body shows refund UNS
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


def _verify_hmac(payload: bytes, secret: str, provided_sig: str) -> bool:
    if not secret or not provided_sig:
        return False
    expected = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_sig)


def _get_shared_secret(env) -> str:
    return (env["ir.config_parameter"].sudo().get_param("iot_token")
            or "").strip("\n").strip()


def _check_hmac_path(env, path: str) -> bool:
    sig = (request.httprequest.headers.get("X-Registry-Signature")
           or "").strip()
    if not sig:
        return False
    secret = _get_shared_secret(env)
    return _verify_hmac(path.encode("utf-8"), secret, sig)


def _check_hmac_body(env) -> tuple[bool, bytes]:
    sig = (request.httprequest.headers.get("X-Registry-Signature")
           or "").strip()
    body = request.httprequest.get_data() or b""
    if not sig:
        return False, body
    secret = _get_shared_secret(env)
    return _verify_hmac(body, secret, sig), body


class L10nBgFpPosOrderStornoController(http.Controller):

    # ─── GET /erp_net_fp/pos_order/<id>/fiscal_receipt ──────────────

    @http.route(
        "/erp_net_fp/pos_order/<int:order_id>/fiscal_receipt",
        type="http", auth="public", methods=["GET"], csrf=False,
        save_session=False,
    )
    def fiscal_receipt_by_id(self, order_id, **_kw):
        sign_path = f"erp_net_fp/pos_order/{order_id}/fiscal_receipt"
        if not _check_hmac_path(request.env, sign_path):
            return _json_response(
                {"error": "X-Registry-Signature mismatch"}, 401)
        Service = (request.env["l10n.bg.erp.net.fp.pos.order.storno"]
                   .sudo().with_context(active_test=False))
        try:
            result = Service.lookup_by_id(int(order_id))
        except Exception:  # noqa: BLE001
            _logger.exception("fiscal_receipt_by_id failed")
            return _json_response(
                {"error": "Internal server error"}, 500)
        http_status = int(result.pop("_http_status", 200))
        return _json_response(result, http_status)

    # ─── GET /erp_net_fp/pos_order/by_uns/<uns>/fiscal_receipt ──────

    @http.route(
        "/erp_net_fp/pos_order/by_uns/<string:uns>/fiscal_receipt",
        type="http", auth="public", methods=["GET"], csrf=False,
        save_session=False,
    )
    def fiscal_receipt_by_uns(self, uns, **_kw):
        sign_path = f"erp_net_fp/pos_order/by_uns/{uns}/fiscal_receipt"
        if not _check_hmac_path(request.env, sign_path):
            return _json_response(
                {"error": "X-Registry-Signature mismatch"}, 401)
        Service = (request.env["l10n.bg.erp.net.fp.pos.order.storno"]
                   .sudo().with_context(active_test=False))
        try:
            result = Service.lookup_by_uns(str(uns).strip())
        except Exception:  # noqa: BLE001
            _logger.exception("fiscal_receipt_by_uns failed")
            return _json_response(
                {"error": "Internal server error"}, 500)
        http_status = int(result.pop("_http_status", 200))
        return _json_response(result, http_status)

    # ─── POST /erp_net_fp/pos_order/<id>/refund_printed ─────────────

    @http.route(
        "/erp_net_fp/pos_order/<int:order_id>/refund_printed",
        type="http", auth="public", methods=["POST"], csrf=False,
        save_session=False,
    )
    def refund_printed(self, order_id, **_kw):
        ok, body = _check_hmac_body(request.env)
        if not ok:
            return _json_response(
                {"error": "X-Registry-Signature mismatch"}, 401)
        try:
            payload = json.loads(body or b"{}")
        except ValueError as exc:
            return _json_response(
                {"error": f"Invalid JSON: {exc}"}, 400)
        Service = (request.env["l10n.bg.erp.net.fp.pos.order.storno"]
                   .sudo().with_context(active_test=False))
        try:
            result = Service.register_refund_printed(
                int(order_id),
                storno_uns=str(payload.get("storno_uns") or "").strip(),
                storno_doc_number=str(
                    payload.get("storno_doc_number") or "").strip(),
                device_serial=str(
                    payload.get("device_serial") or "").strip(),
            )
        except ValueError as exc:
            return _json_response(
                {"ok": False, "error": str(exc)}, 400)
        except Exception:  # noqa: BLE001
            _logger.exception("refund_printed failed")
            return _json_response(
                {"ok": False, "error": "Internal server error"}, 500)
        http_status = int(result.pop("_http_status", 200))
        return _json_response(result, http_status)
