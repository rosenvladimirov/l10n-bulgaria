# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""POST /telegram_agent/inbound — HMAC-подписан вход за Telegram съобщения.

Контракт (огледален на /erpnet_fp/bus/inject):

    Headers:
      X-Tg-Signature: hex(hmac_sha256(body, account.registry_secret))
      X-Tg-Proxy:     <telegram.account.name>

    Body (JSON):
      {
        "v": 1,
        "type": "telegram.message",
        "source": {"proxy": "<account.name>"},
        "data": {"chat_id","sender","sender_id","text","media","msg_id","ts"}
      }

    Отговор: {"ok": true, "channel_id": <telegram.channel id>}
"""
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_MAX_BODY_BYTES = 64 * 1024
_REQUIRED_TOP = ("v", "type", "source", "data")


def _json(payload, status=200):
    return request.make_response(
        json.dumps(payload),
        headers=[("Content-Type", "application/json")], status=status)


class TelegramInboundController(http.Controller):

    @http.route("/telegram_agent/inbound", type="http", auth="public",
                methods=["POST"], csrf=False)
    def inbound(self, **kw):
        body = request.httprequest.get_data() or b""
        if len(body) > _MAX_BODY_BYTES:
            return _json({"error": "Body too large"}, 413)
        try:
            data = json.loads(body or b"{}")
        except ValueError:
            return _json({"error": "Invalid JSON body"}, 400)
        if not isinstance(data, dict):
            return _json({"error": "Body must be a JSON object"}, 400)

        missing = [k for k in _REQUIRED_TOP if k not in data]
        if missing:
            return _json({"error": f"Missing envelope fields: {missing}"}, 400)
        if not isinstance(data["source"], dict) or not data["source"].get("proxy"):
            return _json({"error": "source.proxy required"}, 400)

        sig = (request.httprequest.headers.get("X-Tg-Signature") or "").strip()
        hdr_proxy = (request.httprequest.headers.get("X-Tg-Proxy") or "").strip()
        env_proxy = str(data["source"]["proxy"]).strip()
        if not sig:
            return _json({"error": "X-Tg-Signature header missing"}, 401)
        if hdr_proxy != env_proxy:
            return _json({"error": "X-Tg-Proxy header mismatch"}, 401)

        Account = request.env["telegram.account"].sudo()
        account = Account.search([
            ("name", "=", hdr_proxy), ("registry_secret", "!=", False)], limit=1)
        if not account:
            return _json({"error": "Unknown account — re-pair", "reenrol": True}, 410)
        if account.state == "archived":
            return _json({"error": "Account archived — banned"}, 403)
        if not account.verify_signature(body, sig):
            _logger.warning("telegram_agent: HMAC mismatch for %s", account.name)
            return _json({"error": "Invalid signature"}, 401)

        try:
            channel_id = request.env["telegram.channel"].sudo()._ingest(account, data)
        except Exception:  # noqa: BLE001
            _logger.exception("telegram_agent: ingest failed")
            return _json({"error": "ingest error"}, 500)
        return _json({"ok": True, "channel_id": channel_id})
