# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Shift bridge client — HTTP gateway to the Android ShiftBridgeService.

Replaces the pre-15.10 `shift_close.py` controller + WS subscribe pattern:
Odoo is now the active party, the Android device is a passive TCP service
on port 9103, and the proxy multiplexes everything through one persistent
connection (виж `Odoo.ErpNet.FP/drivers/shifts/tcp_shift_bridge.py`).

Endpoints invoked on the proxy (auth: HMAC-SHA256 X-Registry-Signature
over canonical body, secret = ir.config_parameter('iot_token')):

    GET  <host>/shifts/<serial>/pending
    POST <host>/shifts/<serial>/mark_synced
    GET  <host>/shifts/<serial>/status
    POST <host>/shifts/<serial>/signal

The actual upsert logic (pos.order create, refunds, cash movements,
session close) stays in `l10n.bg.erp.net.fp.shift.sync.apply()` — this
client only orchestrates: pull → apply → mark_synced.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import ssl
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


def _canonicalise(body: dict) -> bytes:
    """Same canonicalisation като proxy + старите shift_close client-и."""
    return json.dumps(body, separators=(",", ":"),
                      sort_keys=True,
                      ensure_ascii=False).encode("utf-8")


def _sign(raw: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw,
                    hashlib.sha256).hexdigest()


class L10nBgFpShiftBridgeClient(models.TransientModel):
    """Stateless HTTP client към Odoo.ErpNet.FP `/shifts/*` endpoints.

    All методи са `@api.model` — викат се чрез
    `env["l10n.bg.erp.net.fp.shift.bridge.client"].sudo().<method>(...)`.
    """

    _name = "l10n.bg.erp.net.fp.shift.bridge.client"
    _description = "BlueCash Shift Bridge HTTP Client"

    # ─── Secret + canonical request helpers ─────────────────────────

    @api.model
    def _shared_secret(self) -> str:
        """ICP `iot_token` — симетричен с proxy `cfg.iot_setup.token`.

        Празен → caller трябва да skip-не device-а с warning (не paired).
        """
        ICP = self.env["ir.config_parameter"].sudo()
        return (ICP.get_param("iot_token") or "").strip("\n").strip()

    def _device_endpoint(self, device, suffix: str) -> str:
        """Build `<host>/shifts/<serial>/<suffix>` от device record.

        `device` е `fiscal.printer.device` (или съвместим record с `host`
        + `l10n_bg_device_serial`).
        """
        host = (getattr(device, "host", "") or "").strip().rstrip("/")
        serial = (getattr(device, "l10n_bg_device_serial", "")
                  or "").strip()
        if not host or not serial:
            raise ValueError(
                "device missing host (%r) or l10n_bg_device_serial (%r)"
                % (host, serial))
        return f"{host}/shifts/{serial}/{suffix.lstrip('/')}"

    def _signed_request(
        self,
        method: str,
        url: str,
        body: dict | None = None,
        timeout: float = 10.0,
    ) -> tuple[int, dict]:
        """Send signed GET/POST. Returns `(http_status, parsed_body)`.

        За GET-ове без body, signature-ът се изчислява над URL path-а
        (същият контракт като proxy `_verify_request`).
        """
        secret = self._shared_secret()
        if not secret:
            return 0, {"error": "iot_token ICP not configured"}
        if body is not None:
            raw = _canonicalise(body)
        else:
            # GET с празно тяло — sign URL path bytes.
            from urllib.parse import urlparse
            raw = urlparse(url).path.encode("utf-8")
        sig = _sign(raw, secret)
        headers = {
            "Content-Type": "application/json",
            "X-Registry-Signature": sig,
            # Cloudflare BIC otherwise rejects no-UA requests (error 1010).
            "User-Agent": "l10n_bg_erp_net_fp/shift-bridge-client",
            "Accept": "application/json",
        }
        # LAN setups често ползват self-signed origin certs; production
        # deployment ползва Cloudflare/origin proper TLS. Мек unverified
        # context (като в pos_session_signal) — за production-grade
        # верификация: ICP toggle.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        if body is not None:
            req = urlrequest.Request(
                url, data=raw, method=method, headers=headers)
        else:
            req = urlrequest.Request(url, method=method, headers=headers)
        try:
            with urlrequest.urlopen(
                    req, timeout=timeout, context=ctx) as resp:
                body_bytes = resp.read()
                try:
                    parsed = json.loads(body_bytes or b"{}")
                except ValueError:
                    parsed = {"raw": body_bytes.decode(
                        "utf-8", errors="replace")[:500]}
                return resp.status, parsed
        except HTTPError as exc:
            try:
                parsed = json.loads(exc.read() or b"{}")
            except (ValueError, OSError):
                parsed = {"error": exc.reason}
            return exc.code, parsed
        except URLError as exc:
            return 0, {"error": f"transport: {exc.reason}"}
        except Exception as exc:  # noqa: BLE001
            _logger.exception("shift bridge client request failed: %s", url)
            return 0, {"error": str(exc)}

    # ─── Public API (called from cron / hooks / wizard) ────────────

    @api.model
    def pull_pending(self, device) -> dict:
        """GET pending shifts от Android (proxy multiplexes).

        Връща `{"http_status", "shifts": [...]}`. Празен list при no pending.
        """
        url = self._device_endpoint(device, "pending")
        http_status, parsed = self._signed_request("GET", url)
        return {
            "http_status": http_status,
            "shifts": list(parsed.get("shifts") or []),
            "error": parsed.get("error") if http_status >= 400 else None,
        }

    @api.model
    def mark_synced(
        self,
        device,
        shift_id: int,
        odoo_session_id: int,
        synced_at: str,
    ) -> dict:
        """POST `/mark_synced` — Android чисти `pending` за този shift."""
        url = self._device_endpoint(device, "mark_synced")
        body = {
            "shift_id": int(shift_id),
            "odoo_session_id": int(odoo_session_id),
            "synced_at": synced_at,
        }
        http_status, parsed = self._signed_request("POST", url, body=body)
        return {
            "http_status": http_status,
            "ok": bool(parsed.get("ok", False)) if http_status < 400 else False,
            "error": parsed.get("error") if http_status >= 400 else None,
        }

    @api.model
    def query_status(self, device) -> dict:
        """GET `/status` — live state на устройството."""
        url = self._device_endpoint(device, "status")
        http_status, parsed = self._signed_request("GET", url)
        return {
            "http_status": http_status,
            "open_shift": parsed.get("open_shift"),
            "pending_count": int(parsed.get("pending_count") or 0),
            "last_z_at": parsed.get("last_z_at"),
            "error": parsed.get("error") if http_status >= 400 else None,
        }

    @api.model
    def emit_signal(
        self,
        device,
        event_type: str,
        payload: dict,
    ) -> dict:
        """POST `/signal` — Odoo bash-ва shift.open / shift.close.request."""
        url = self._device_endpoint(device, "signal")
        body = dict(payload or {})
        body["type"] = event_type
        http_status, parsed = self._signed_request("POST", url, body=body)
        return {
            "http_status": http_status,
            "ok": bool(parsed.get("ok", False)) if http_status < 400 else False,
            "acknowledged": bool(parsed.get("acknowledged", False)),
            "error": parsed.get("error") if http_status >= 400 else None,
        }

    # ─── Orchestration: pull → apply → mark ────────────────────────

    @api.model
    def apply_pending(self, device) -> dict:
        """Full sync cycle за един device.

        1. Pull pending shifts от Android.
        2. За всеки → delegate to `l10n.bg.erp.net.fp.shift.sync.apply()`.
        3. При success → POST mark_synced обратно към Android.

        Връща dict с counts + warnings; идемпотентно (повторното
        извикване на същия shift връща `{"already_synced": ...}` от
        downstream service защото UNS-итe вече съществуват като
        pos.order).
        """
        out = {
            "device_serial": getattr(device, "l10n_bg_device_serial", ""),
            "pulled": 0,
            "applied": 0,
            "marked": 0,
            "errors": [],
            "warnings": [],
        }
        pull = self.pull_pending(device)
        if pull.get("error"):
            out["errors"].append(
                _("pull failed: %s") % pull["error"])
            return out
        shifts = pull.get("shifts") or []
        out["pulled"] = len(shifts)
        if not shifts:
            return out
        Service = (self.env["l10n.bg.erp.net.fp.shift.sync"]
                   .sudo().with_context(active_test=False))
        for payload in shifts:
            try:
                # The sync_service expects `device_serial` в payload;
                # proxy strips it (sits в URL), затова го re-injectваме.
                p = dict(payload)
                p.setdefault("device_serial",
                             out["device_serial"])
                result = Service.apply(p, dry_run=False)
            except ValueError as exc:
                _logger.info(
                    "shift apply validation error for shift %s: %s",
                    payload.get("z_report_number"), exc)
                out["errors"].append(
                    _("apply failed for Z %(z)s: %(e)s") % {
                        "z": payload.get("z_report_number"),
                        "e": exc,
                    })
                continue
            except Exception as exc:  # noqa: BLE001
                _logger.exception(
                    "shift apply crashed for shift %s",
                    payload.get("z_report_number"))
                out["errors"].append(
                    _("apply crashed for Z %(z)s: %(e)s") % {
                        "z": payload.get("z_report_number"),
                        "e": exc,
                    })
                continue
            out["applied"] += 1
            out["warnings"].extend(result.get("warnings") or [])
            shift_id = (payload.get("shift_id")
                        or payload.get("z_report_number"))
            mark = self.mark_synced(
                device,
                shift_id=shift_id,
                odoo_session_id=result.get("odoo_session_id", 0),
                synced_at=fields.Datetime.now().isoformat() + "Z",
            )
            if mark.get("ok"):
                out["marked"] += 1
            else:
                out["warnings"].append(
                    _("mark_synced failed for shift %(s)s: %(e)s") % {
                        "s": shift_id,
                        "e": mark.get("error") or mark.get("http_status"),
                    })
        return out

    @api.model
    def cron_apply_all_devices(self) -> None:
        """Cron entry-point: iterate paired devices, pull + apply each.

        Iterates `fiscal.printer.device` records that имат
        `l10n_bg_device_serial` set AND `host` set. Proxy ще върне
        404 за non-shift-paired devices — третираме като skip.
        """
        Device = self.env["fiscal.printer.device"].sudo()
        devices = Device.search([
            ("l10n_bg_device_serial", "!=", False),
            ("l10n_bg_device_serial", "!=", ""),
            ("host", "!=", False),
            ("host", "!=", ""),
        ])
        if not devices:
            _logger.debug("shift bridge cron: no paired devices found")
            return
        for dev in devices:
            try:
                result = self.apply_pending(dev)
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "shift bridge cron: failed for device %s",
                    dev.display_name)
                continue
            if result["pulled"]:
                _logger.info(
                    "shift bridge cron: device %s — pulled=%d applied=%d "
                    "marked=%d warnings=%d errors=%d",
                    dev.display_name, result["pulled"], result["applied"],
                    result["marked"], len(result["warnings"]),
                    len(result["errors"]))
