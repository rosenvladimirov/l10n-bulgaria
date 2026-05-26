# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""POST /erpnet_fp/bus/inject — HMAC-signed live-event firehose.

Контракт: виж `docs/proxy_push_schema.md` в този модул. Накратко:

    Headers:
      X-Bus-Inject-Signature: hex(hmac_sha256(body, secret))
      X-Bus-Inject-Proxy:     <proxy.name>

    Body:
      {
        "v": 1,
        "type": "plate.detected",
        "source": {proxy, device, device_kind},
        "data": {...}
      }

    Server-stamped on success:
      ts (UTC ISO-8601), id (UUID4 if absent)

    Response: {ok: true, id: <event-id>}

Validation order:
  1. Body is JSON dict
  2. envelope `v`, `type`, `source.proxy`, `data` present
  3. X-Bus-Inject-Proxy header present + matches `source.proxy`
  4. HMAC verifies against the matched proxy.registry_secret
  5. proxy.state in ('active', 'pairing') — archived proxies are banned

Errors are short JSON `{"error": "msg"}` with 400/401/403/410.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone

from odoo import _, fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

# The channel name is part of the public contract — exported so plugin
# modules and JS subscribers reference it from one place.
PROXY_EVENTS_CHANNEL = "erpnet_fp_proxy_events"

# Required keys in the envelope (top level + nested source).
_REQUIRED_TOP = ("v", "type", "source", "data")
_REQUIRED_SOURCE = ("proxy",)

# Max accepted body size — guard against accidental dumps.  Live signals
# should stay small; if a payload genuinely needs MB the operator should
# use a persisted HTTP endpoint instead.
_MAX_BODY_BYTES = 64 * 1024


def _json_response(payload: dict, status: int = 200):
    return request.make_response(
        json.dumps(payload),
        headers=[("Content-Type", "application/json")],
        status=status,
    )


def _verify_hmac(body: bytes, secret: str, sig_hex: str) -> bool:
    """Constant-time HMAC verify. Same scheme as the Fleet heartbeat
    controller — copying the algorithm here (NOT the function) to keep
    the dependency surface tiny."""
    if not secret or not sig_hex:
        return False
    expected = hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    try:
        return hmac.compare_digest(expected, sig_hex.strip())
    except (TypeError, ValueError):
        return False


class BusInjectController(http.Controller):

    @http.route(
        "/erpnet_fp/bus/inject",
        type="http", auth="public", methods=["POST"], csrf=False,
    )
    def bus_inject(self, **kw):
        body = request.httprequest.get_data() or b""
        if len(body) > _MAX_BODY_BYTES:
            return _json_response(
                {"error": f"Body too large (>{_MAX_BODY_BYTES} bytes); "
                          "bus_inject is for live signals only — use an HTTP-"
                          "with-record endpoint for big payloads."}, 413)

        try:
            data = json.loads(body or b"{}")
        except ValueError:
            return _json_response({"error": "Invalid JSON body"}, 400)
        if not isinstance(data, dict):
            return _json_response(
                {"error": "Body must be a JSON object"}, 400)

        # Envelope shape validation
        missing_top = [k for k in _REQUIRED_TOP if k not in data]
        if missing_top:
            return _json_response(
                {"error": f"Missing envelope fields: {missing_top}"}, 400)
        if not isinstance(data["source"], dict):
            return _json_response(
                {"error": "source must be an object"}, 400)
        missing_src = [k for k in _REQUIRED_SOURCE if not data["source"].get(k)]
        if missing_src:
            return _json_response(
                {"error": f"Missing source fields: {missing_src}"}, 400)

        # Auth
        sig = (request.httprequest.headers.get("X-Bus-Inject-Signature")
               or "").strip()
        hdr_proxy = (request.httprequest.headers.get("X-Bus-Inject-Proxy")
                     or "").strip()
        env_proxy = str(data["source"]["proxy"]).strip()
        if not sig:
            return _json_response(
                {"error": "X-Bus-Inject-Signature header missing"}, 401)
        if not hdr_proxy:
            return _json_response(
                {"error": "X-Bus-Inject-Proxy header missing"}, 401)
        if hdr_proxy != env_proxy:
            return _json_response(
                {"error": "X-Bus-Inject-Proxy header doesn't match "
                          "source.proxy in body"}, 401)

        Proxy = request.env["erpnet.fp.proxy"].sudo()
        proxy = Proxy.search([
            ("name", "=", hdr_proxy),
            ("registry_secret", "!=", False),
        ], limit=1)
        if not proxy:
            _logger.warning(
                "bus_inject: no proxy registered as %r — rejecting", hdr_proxy)
            return _json_response(
                {"error": "Unknown proxy — please re-enrol",
                 "reenrol": True}, 410)
        if proxy.state == "archived":
            return _json_response(
                {"error": "Proxy archived — banned", "banned": True}, 403)
        if not _verify_hmac(body, proxy.registry_secret, sig):
            _logger.warning(
                "bus_inject: HMAC mismatch for proxy %s — rejecting",
                proxy.name)
            return _json_response(
                {"error": "Invalid signature"}, 401)

        # Server-side stamps (idempotency-friendly — if proxy already
        # sent an id, keep it; else generate)
        event_id = str(data.get("id") or uuid.uuid4())
        ts = data.get("ts") or datetime.now(timezone.utc).isoformat(
            timespec="milliseconds").replace("+00:00", "Z")
        msg = {
            "v": data.get("v", 1),
            "type": data["type"],
            "source": data["source"],
            "ts": ts,
            "id": event_id,
            "data": data["data"],
        }

        # Publish onto bus.bus — broadcast on the canonical channel.
        # No DB record is created BY THIS CONTROLLER (per
        # docs/proxy_push_schema.md). Downstream addons (e.g.
        # hr_attendance_access_control) MAY implement
        # `_on_proxy_event(envelope)` on a model whose _name matches
        # one of the hook targets below — bus_inject calls them after
        # publishing, so they can persist / react without taking a hard
        # dependency on this module.
        request.env["bus.bus"]._sendone(
            PROXY_EVENTS_CHANNEL, PROXY_EVENTS_CHANNEL, msg)

        # Soft hooks — fire-and-forget. Errors in a hook MUST NOT break
        # the bus publish path: the live signal is the primary contract,
        # persistence is secondary. Each hook target is checked with
        # `in self.env` (model registry) so a missing addon is silent.
        for hook_model in ("hr.rfid.event", "access.proxy.bridge"):
            try:
                Model = request.env.get(hook_model)
                if Model is None or not hasattr(Model, "_on_proxy_event"):
                    continue
                Model.sudo()._on_proxy_event(msg)
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "bus_inject hook %s failed for envelope id=%s type=%s",
                    hook_model, event_id, msg.get("type"))

        return _json_response({"ok": True, "id": event_id, "channel": PROXY_EVENTS_CHANNEL})
