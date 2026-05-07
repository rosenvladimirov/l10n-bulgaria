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

# Bus channel that the kanban auto-refresh JS listens on. Anyone with
# read access to the proxy fleet subscribes; the message payload
# carries minimal record info so the client can decide whether to
# reload the view.
_FLEET_BUS_CHANNEL = "erpnet_fp_fleet"


def _notify_fleet(env, kind: str, proxy) -> None:
    """Push a `fleet_update` event onto the bus so any open Fleet view
    auto-refreshes. `kind` is one of: enrol_new, enrol_refresh, heartbeat,
    banned."""
    try:
        env["bus.bus"]._sendone(_FLEET_BUS_CHANNEL, "fleet_update", {
            "kind": kind,
            "id": proxy.id if proxy else None,
            "name": proxy.name if proxy else "",
            "state": proxy.state if proxy else "",
        })
    except Exception:  # noqa: BLE001
        # Never let bus failure block the heartbeat handler.
        _logger.exception("Bus notify failed")


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

    # ─── POST /erp_net_fp/registry/auto-enrol ────────────────────

    @http.route(
        "/erp_net_fp/registry/auto-enrol",
        type="http", auth="public", methods=["POST"], csrf=False,
    )
    def registry_auto_enrol(self, **kw):
        """Zero-touch enrolment using the proxy's admin_token as
        proof-of-possession.

        A fresh proxy starts with:
          * URL hardcoded in config.yaml (default iot.mcpworks.net)
          * admin_token auto-bootstrapped on first run
            (`/admin/bootstrap-info` flow, RFC1918-restricted, single-claim)

        On startup it POSTs here with `{name, host, version, admin_token}`
        and gets back `{secret, name}`. From that moment the proxy
        heartbeats with HMAC-signed bodies as in the manual flow.

        Idempotency: if a record with matching `name` already exists,
        we either:
          * accept (admin_token matches the stored one, or no stored
            token yet) — refresh secret + return
          * reject 409 (admin_token mismatches) — operator must reset
            via the UI
        If no record exists, create one with state=active.

        This is opt-in via `server.registry.enabled: true` on the
        proxy. There is intentionally no shared enrolment secret —
        the per-proxy admin_token is the unit of authentication.
        """
        try:
            raw = request.httprequest.get_data() or b""
            data = json.loads(raw or b"{}")
        except ValueError:
            return _json_response({"error": "Invalid JSON body"}, 400)

        name = (data.get("name") or "").strip()
        host = (data.get("host") or "").strip()
        version = (data.get("version") or "").strip()
        admin_token = (data.get("admin_token") or "").strip()
        public_url = (data.get("public_url") or "").rstrip("/")
        if not (name and admin_token):
            return _json_response(
                {"error": "name + admin_token required"}, 400)

        Proxy = request.env["erpnet.fp.proxy"].sudo()
        existing = Proxy.search([("name", "=", name)], limit=1)
        new_secret = secrets.token_urlsafe(32)

        if existing:
            # Archived = banned. Operator must Unarchive the record
            # before this proxy can re-enrol. The proxy's admin_token
            # remains valid to call /admin/* but it can no longer
            # heartbeat or appear in the active fleet.
            if existing.state == "archived":
                _logger.warning(
                    "Auto-enrol BANNED: proxy %r is archived "
                    "(host=%r).", name, host)
                _notify_fleet(request.env, "banned", existing)
                return _json_response(
                    {"error": "Proxy archived — banned. Unarchive in the "
                              "Fleet UI to allow re-enrolment.",
                     "banned": True},
                    403)
            stored = existing.get_admin_token()
            if stored and stored != admin_token:
                _logger.warning(
                    "Auto-enrol rejected: name=%r admin_token mismatch "
                    "(host=%r). Operator must Reset Secret in UI to "
                    "allow re-enrolment.", name, host)
                return _json_response(
                    {"error": "Name taken — admin token mismatch. "
                              "Reset Secret in the Fleet UI to re-enrol."},
                    409)
            existing_vals = {
                "registry_secret": new_secret,
                "host": host or existing.host,
                "version": version or existing.version,
                "state": "active",
                "last_seen": fields.Datetime.now(),
            }
            if public_url:
                existing_vals["url"] = public_url
            existing.write(existing_vals)
            existing.set_admin_token(admin_token)
            existing.message_post(body=(
                f"Proxy auto-enrolled (host={host!r}, version={version!r})."
            ))
            _logger.info("Proxy %s auto-enrolled (host=%s, version=%s)",
                         name, host, version)
            _notify_fleet(request.env, "enrol_refresh", existing)
            return _json_response({"secret": new_secret, "name": name})

        # New record — accept open enrolment.
        new_vals = {
            "name": name,
            "host": host,
            "version": version,
            "registry_secret": new_secret,
            "state": "active",
            "last_seen": fields.Datetime.now(),
        }
        if public_url:
            new_vals["url"] = public_url
        rec = Proxy.create(new_vals)
        rec.set_admin_token(admin_token)
        rec.message_post(body=(
            f"Proxy auto-enrolled — first-time registration "
            f"(host={host!r}, version={version!r})."
        ))
        _logger.info("New proxy %s auto-enrolled (host=%s, version=%s)",
                     name, host, version)
        _notify_fleet(request.env, "enrol_new", rec)
        return _json_response({"secret": new_secret, "name": name})

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
            # Two distinct cases:
            #   * Operator deleted the record → proxy should re-enrol
            #     immediately (returns 410 Gone, proxy clears its
            #     local secret and falls back to auto-enrol).
            #   * Operator archived the record → ban; proxy must NOT
            #     re-enrol (returns 403 Forbidden).
            # Disambiguate by checking for any record (incl. archived)
            # whose secret would have validated the HMAC.
            archived = Proxy.search([
                ("registry_secret", "!=", False),
                ("state", "=", "archived"),
            ])
            for cand in archived:
                if _verify_hmac(body, cand.registry_secret, sig):
                    _logger.warning(
                        "Heartbeat rejected — proxy %r is archived",
                        cand.name)
                    _notify_fleet(request.env, "banned", cand)
                    return _json_response(
                        {"error": "Proxy archived — banned",
                         "banned": True},
                        403)
            _logger.warning("Heartbeat rejected — no proxy matched HMAC "
                            "(host=%r). Proxy will re-enrol.", host)
            return _json_response(
                {"error": "Unknown proxy — please re-enrol",
                 "reenrol": True},
                410)

        # Apply the heartbeat
        version = (data.get("version") or "").strip()
        new_host = (data.get("host") or host or "").strip()
        admin_token = (data.get("admin_token") or "").strip()
        public_url = (data.get("public_url") or "").rstrip("/")
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
        # Only overwrite URL if proxy reported one — keep manual edits
        # done by admin in the form view if proxy doesn't know its
        # public URL (e.g. local-only dev proxies).
        if public_url:
            vals["url"] = public_url
        proxy.write(vals)
        if admin_token:
            try:
                proxy.set_admin_token(admin_token)
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "Failed to encrypt+store admin token for proxy %s",
                    proxy.name)
        _notify_fleet(request.env, "heartbeat", proxy)
        return _json_response({"ok": True, "name": proxy.name})
