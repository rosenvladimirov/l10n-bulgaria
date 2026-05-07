# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Public-facing registry endpoints for ErpNet.FP fleet enrolment.

Routes:
    POST /erp_net_fp/registry/pair       — exchange one-time pairing
                                           token for long-lived secret
    POST /erp_net_fp/registry/heartbeat  — accept HMAC-signed status

Both routes are ``auth='public'`` because the proxy is not an Odoo
user; authentication happens via the pairing token (one-time) or
the registry secret (HMAC-SHA256 of the request body).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets

from odoo import fields, http
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


def _json_response(payload: dict, status: int = 200) -> Response:
    return Response(
        json.dumps(payload),
        status=status,
        content_type="application/json",
    )


def _verify_hmac(body: bytes, secret: str, provided_sig: str) -> bool:
    if not secret or not provided_sig:
        return False
    expected = hmac.new(secret.encode("utf-8"), body,
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_sig)


class ErpNetFpRegistryController(http.Controller):

    # ─── POST /erp_net_fp/registry/pair ──────────────────────────

    @http.route(
        "/erp_net_fp/registry/pair",
        type="http", auth="public", methods=["POST"], csrf=False,
    )
    def registry_pair(self, **kw):
        """Exchange a one-time pairing token for a long-lived secret.

        Body (JSON): {pairing_token, host, version}
        Returns:    {secret} on success, {error} otherwise.
        """
        try:
            raw = request.httprequest.get_data() or b""
            data = json.loads(raw or b"{}")
        except ValueError:
            return _json_response({"error": "Invalid JSON body"}, 400)

        token = (data.get("pairing_token") or "").strip()
        host = (data.get("host") or "").strip()
        version = (data.get("version") or "").strip()
        if not token:
            return _json_response({"error": "pairing_token required"}, 400)

        Proxy = request.env["erpnet.fp.proxy"].sudo()
        proxy = Proxy.search([("pairing_token", "=", token)], limit=1)
        if not proxy:
            _logger.warning("Pairing rejected — unknown token")
            return _json_response({"error": "Invalid pairing token"}, 401)
        if not proxy.pairing_expires or proxy.pairing_expires < fields.Datetime.now():
            _logger.warning("Pairing rejected — expired token for proxy %s",
                            proxy.name)
            proxy.write({"pairing_token": False, "pairing_expires": False})
            return _json_response({"error": "Pairing token expired"}, 401)

        # Single-use: regenerate registry secret AND wipe the pairing token.
        new_secret = secrets.token_urlsafe(32)
        proxy.write({
            "pairing_token": False,
            "pairing_expires": False,
            "registry_secret": new_secret,
            "host": host or proxy.host,
            "version": version or proxy.version,
            "state": "active",
            "last_seen": fields.Datetime.now(),
        })
        proxy.message_post(body=(
            f"Proxy paired from host={host!r}, version={version!r}."
        ))
        _logger.info("Proxy %s paired (host=%s, version=%s)",
                     proxy.name, host, version)
        return _json_response({"secret": new_secret, "name": proxy.name})

    # ─── POST /erp_net_fp/registry/heartbeat ─────────────────────

    @http.route(
        "/erp_net_fp/registry/heartbeat",
        type="http", auth="public", methods=["POST"], csrf=False,
    )
    def registry_heartbeat(self, **kw):
        """Accept a heartbeat from a paired proxy.

        Body (JSON): {host, version, admin_token, devices: {...}}
        Headers:     X-Registry-Signature: HMAC-SHA256(body, secret) hex
                     X-Registry-Host: hostname (used to lookup proxy
                       only as a hint — actual auth is HMAC over
                       the secret of the matched record)

        Lookup strategy: search across all active proxies for one
        whose secret validates the HMAC. Slow at fleet scale; if we
        ever cross ~500 proxies, switch to a key-id header.
        """
        body = request.httprequest.get_data() or b""
        try:
            data = json.loads(body or b"{}")
        except ValueError:
            return _json_response({"error": "Invalid JSON body"}, 400)

        sig = (request.httprequest.headers.get("X-Registry-Signature")
               or "").strip()
        host = (request.httprequest.headers.get("X-Registry-Host")
                or data.get("host") or "").strip()
        if not sig:
            return _json_response({"error": "X-Registry-Signature header missing"}, 401)

        Proxy = request.env["erpnet.fp.proxy"].sudo()
        # Optimisation: try host-matching first, fall back to scan.
        candidates = (host and Proxy.search([
            ("registry_secret", "!=", False),
            ("state", "in", ("active", "pairing")),
            ("host", "=", host),
        ])) or Proxy.search([
            ("registry_secret", "!=", False),
            ("state", "in", ("active", "pairing")),
        ])
        proxy = None
        for cand in candidates:
            if _verify_hmac(body, cand.registry_secret, sig):
                proxy = cand
                break
        if proxy is None:
            _logger.warning("Heartbeat rejected — no proxy matched HMAC "
                            "(host=%r)", host)
            return _json_response({"error": "Invalid signature"}, 401)

        # Apply the heartbeat
        version = (data.get("version") or "").strip()
        new_host = (data.get("host") or host or "").strip()
        admin_token = (data.get("admin_token") or "").strip()
        devices = data.get("devices") or {}
        try:
            devices_json = json.dumps(devices, sort_keys=True)
        except (TypeError, ValueError):
            devices_json = "{}"
        vals = {
            "last_seen": fields.Datetime.now(),
            "version": version or proxy.version,
            "host": new_host or proxy.host,
            "devices_json": devices_json,
            "state": "active",
        }
        proxy.write(vals)
        if admin_token:
            try:
                proxy.set_admin_token(admin_token)
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "Failed to encrypt+store admin token for proxy %s",
                    proxy.name)
        return _json_response({"ok": True, "name": proxy.name})
