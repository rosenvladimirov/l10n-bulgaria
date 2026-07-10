# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""POST /erpnet_fp/cfx/ingest — HMAC-signed CFX AUDIT ingestion.

Персистиращият (audit/stats) път за CFX събития. За разлика от
bus_inject (live-only, no DB), този controller ЗАПИСВА машинни
статистики и dispatch-ва по `machine_kind`:

    europlacer → europlacer.trac / europlacer.trac.line
                 (soft dep mrp_europlacer_trac; env-check, no manifest dep)
    parmi/oven/laser/generic → cfx.machine.stat

Auth схемата е ИДЕНТИЧНА на bus_inject (копираме алгоритъма, не
модула, за да държим dependency surface-а минимален):

    Headers:
      X-Bus-Inject-Signature: hex(hmac_sha256(raw_body, proxy.registry_secret))
      X-Bus-Inject-Proxy:     <proxy.name>

    Body (CFX event):
      {
        "v": 1,
        "proxy": "<proxy.name>",          # optional; header е авторитетен
        "machine_kind": "europlacer",
        "cfx_handle": "Europlacer.Line1.RC",
        "message_name": "MaterialsInstalled",
        "transaction_id": "…",
        "workorder": "WH/MO/00001",        # optional WO key за live refresh
        "ts": "…",                          # optional ISO-8601
        "data": {…}                         # CFX-specific payload
      }

    Response: {ok: true, machine_kind, persisted, stat_id?}

WS/live (uniform): ако събитието носи work-order ключ, публикуваме на
канала `erpnet_fp_proxy_events` envelope с `data._refresh` hint към
mrp.workorder — l10n_bg_live_refresh пребоядисва отворените форми БЕЗ
нов JS. Пътят е ЕДНАКЪВ за всички machine_kind.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone

from odoo import http
from odoo.http import request

from ..models.cfx_extractors import extract

_logger = logging.getLogger(__name__)

# Публичен контракт — същият канал, който bus_inject/live_refresh ползват.
PROXY_EVENTS_CHANNEL = "erpnet_fp_proxy_events"

_MAX_BODY_BYTES = 256 * 1024  # audit payload-ите може да носят matrix rows

# CFX message class → bus event type (за _TOAST_KIND fan-out).
_EVENT_TYPE_MAP = {
    "WorkStarted": "cfx.work_started",
    "MaterialsInstalled": "cfx.materials_installed",
    "WorkCompleted": "cfx.work_completed",
    "StationStateChanged": "cfx.station_state",
    "FaultOccurred": "cfx.fault",
    "UnitsInspected": "cfx.wo_progress",
    "UnitsProcessed": "cfx.wo_progress",
}


def _json_response(payload: dict, status: int = 200):
    return request.make_response(
        json.dumps(payload),
        headers=[("Content-Type", "application/json")],
        status=status,
    )


def _verify_hmac(body: bytes, secret: str, sig_hex: str) -> bool:
    """Constant-time HMAC verify — същата схема като bus_inject/heartbeat."""
    if not secret or not sig_hex:
        return False
    expected = hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    try:
        return hmac.compare_digest(expected, sig_hex.strip())
    except (TypeError, ValueError):
        return False


def _now_iso():
    return datetime.now(timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


class CfxIngestController(http.Controller):

    # Dispatch registry по machine_kind → име на handler метод (string,
    # резолва се с getattr на инстанцията, за да няма bound-method капан
    # при дефиниране на класа). Само `machine_kind` избира handler-а —
    # това е REST/stats machine-kind routing-ът от PLAN §4.
    _HANDLERS = {
        "europlacer": "_ingest_europlacer",
        "parmi": "_ingest_parmi",
        "oven": "_ingest_oven",
        "laser": "_ingest_laser",
        "generic": "_ingest_generic",
    }

    # ─── Route ────────────────────────────────────────────────────
    @http.route(
        "/erpnet_fp/cfx/ingest",
        type="http", auth="public", methods=["POST"], csrf=False,
    )
    def cfx_ingest(self, **kw):
        body = request.httprequest.get_data() or b""
        if len(body) > _MAX_BODY_BYTES:
            return _json_response(
                {"error": f"Body too large (>{_MAX_BODY_BYTES} bytes)"}, 413)
        try:
            event = json.loads(body or b"{}")
        except ValueError:
            return _json_response({"error": "Invalid JSON body"}, 400)
        if not isinstance(event, dict):
            return _json_response(
                {"error": "Body must be a JSON object"}, 400)

        machine_kind = (event.get("machine_kind") or "").strip()
        message_name = (event.get("message_name") or "").strip()
        if not machine_kind:
            return _json_response({"error": "machine_kind is required"}, 400)
        if not message_name:
            return _json_response({"error": "message_name is required"}, 400)

        # ── Auth (идентична на bus_inject) ──
        sig = (request.httprequest.headers.get("X-Bus-Inject-Signature")
               or "").strip()
        hdr_proxy = (request.httprequest.headers.get("X-Bus-Inject-Proxy")
                     or "").strip()
        if not sig:
            return _json_response(
                {"error": "X-Bus-Inject-Signature header missing"}, 401)
        if not hdr_proxy:
            return _json_response(
                {"error": "X-Bus-Inject-Proxy header missing"}, 401)
        body_proxy = str(event.get("proxy") or "").strip()
        if body_proxy and body_proxy != hdr_proxy:
            return _json_response(
                {"error": "X-Bus-Inject-Proxy header doesn't match "
                          "`proxy` in body"}, 401)

        Proxy = request.env["erpnet.fp.proxy"].sudo()
        proxy = Proxy.search([
            ("name", "=", hdr_proxy),
            ("registry_secret", "!=", False),
        ], limit=1)
        if not proxy:
            _logger.warning(
                "cfx/ingest: no proxy registered as %r — rejecting", hdr_proxy)
            return _json_response(
                {"error": "Unknown proxy — please re-enrol",
                 "reenrol": True}, 410)
        if proxy.state == "archived":
            return _json_response(
                {"error": "Proxy archived — banned", "banned": True}, 403)
        if not _verify_hmac(body, proxy.registry_secret, sig):
            _logger.warning(
                "cfx/ingest: HMAC mismatch for proxy %s — rejecting",
                proxy.name)
            return _json_response({"error": "Invalid signature"}, 401)

        # ── Dispatch по machine_kind ──
        handler_name = self._HANDLERS.get(
            machine_kind, self._HANDLERS["generic"])
        handler = getattr(self, handler_name)
        env = request.env
        try:
            result = handler(env, proxy, event) or {}
        except Exception:  # noqa: BLE001
            _logger.exception(
                "cfx/ingest handler %s failed (proxy=%s kind=%s msg=%s)",
                handler_name, proxy.name, machine_kind, message_name)
            return _json_response(
                {"error": "Handler failed — see server log"}, 500)

        # ── WS/live: uniform mrp.workorder population (всеки kind) ──
        try:
            self._emit_wo_refresh(env, proxy, event)
        except Exception:  # noqa: BLE001
            # Live е secondary; persist-ът вече е успял.
            _logger.exception(
                "cfx/ingest: WO refresh emit failed (proxy=%s)", proxy.name)

        return _json_response({
            "ok": True,
            "machine_kind": machine_kind,
            "message_name": message_name,
            **result,
        })

    # ─── WS/live uniform WO population ────────────────────────────
    def _wo_key(self, event):
        """Извади work-order ключ от събитието, ако носи такъв."""
        data = event.get("data") or {}
        return (event.get("workorder")
                or data.get("workorder")
                or data.get("wo_name")
                or data.get("work_order")
                or None)

    def _emit_wo_refresh(self, env, proxy, event):
        """Публикувай live update UNIFORMLY в mrp.workorder.

        Строим bus envelope (същата форма като bus_inject) с
        `data._refresh` hint към mrp.workorder, matched by name. При
        отворена MO/WO форма l10n_bg_live_refresh я пребоядисва —
        нула нов frontend код. Пътят е идентичен за ВСЯКА машина.
        """
        wo_name = self._wo_key(event)
        if not wo_name:
            return  # няма WO контекст — нищо за refresh
        data = event.get("data") or {}
        msg_name = (event.get("message_name") or "").strip()
        ev_type = _EVENT_TYPE_MAP.get(msg_name, "cfx.wo_progress")
        # Кое поле да флашнем: при work-completed → state, иначе прогрес.
        refresh_field = ("state" if ev_type == "cfx.work_completed"
                         else "qty_produced")
        refresh_hints = [{
            "model": "mrp.workorder",
            "match_field": "name",
            "match_value": str(wo_name),
            "field": refresh_field,
            "mode": "field",
        }]
        # Placed-component брой (само за MaterialsInstalled) — храни
        # ephemeral overlay значката на Shop Floor картата
        # (mrp_shopfloor_cfx_live). Additive; None ако не е приложимо.
        placed = None
        if msg_name == "MaterialsInstalled":
            materials = data.get("materials") or data.get("installed") or []
            if isinstance(materials, list):
                placed = len(materials)
        envelope = {
            "v": 1,
            "type": ev_type,
            "source": {
                "proxy": proxy.name,
                "device": event.get("cfx_handle") or "",
                "device_kind": "cfx",
            },
            "ts": event.get("ts") or _now_iso(),
            "id": str(event.get("id") or uuid.uuid4()),
            "data": {
                "workorder": str(wo_name),
                # Явен алиас за Shop Floor patch-а (чете workorder|wo_name).
                "wo_name": str(wo_name),
                "machine_kind": event.get("machine_kind"),
                "message_name": msg_name,
                # Пренасяме няколко разпознаваеми числови стойности за toast.
                "qty": data.get("qty") or data.get("quantity"),
                "placed": placed,
                "state": data.get("state") or data.get("result"),
                "_refresh": refresh_hints,
            },
        }
        env["bus.bus"].sudo()._sendone(
            PROXY_EVENTS_CHANNEL, PROXY_EVENTS_CHANNEL, envelope)

    # ─── Handlers (REST/stats machine-kind-routed) ────────────────
    def _ingest_europlacer(self, env, proxy, event):
        """SOFT-интеграция с europlacer.trac/.line (mrp_europlacer_trac).

        Ако схемата липсва на този стек → log-skip (без manifest dep —
        модулът е в друго repo). WorkStarted → trac header; Work-
        Completed → resolve header; MaterialsInstalled → trac.line rows.
        """
        Trac = env.get("europlacer.trac")
        if Trac is None:
            _logger.info(
                "cfx/ingest europlacer: mrp_europlacer_trac not installed "
                "on this stack — skipping persist (proxy=%s)", proxy.name)
            return {"persisted": False, "reason": "schema-absent"}

        Trac = Trac.sudo()
        Line = env["europlacer.trac.line"].sudo()
        msg = (event.get("message_name") or "").strip()
        txn = event.get("transaction_id") or ""
        data = event.get("data") or {}
        cfx_handle = event.get("cfx_handle") or ""

        header = False
        if txn:
            header = Trac.search([("transaction_id", "=", txn)], limit=1)

        if msg == "WorkStarted":
            if not header:
                header = Trac.create({
                    "name": data.get("name") or txn or f"CFX {cfx_handle}",
                    "transaction_id": txn,
                    "cfx_handle": cfx_handle,
                    "source_mode": "cfx",
                    "dummy_workorder_id": self._wo_key(event) or "",
                    "batch": data.get("batch") or "",
                    "begin_date_trac": self._parse_dt(
                        data.get("start") or event.get("ts")),
                    "station_state": data.get("state") or "",
                })
            return {"persisted": True, "trac_id": header.id, "role": "header"}

        if msg == "WorkCompleted":
            if header:
                header.write({
                    "result": data.get("result") or "Completed",
                    "end_date_trac": self._parse_dt(
                        data.get("end") or event.get("ts")),
                    "station_state": data.get("state") or header.station_state,
                })
            return {"persisted": bool(header),
                    "trac_id": header.id if header else False,
                    "role": "header-complete"}

        if msg == "MaterialsInstalled":
            if not header:
                # Материали без header → създай lightweight header, за да
                # закачим линиите (може WorkStarted да е пропуснат).
                header = Trac.create({
                    "name": txn or f"CFX {cfx_handle}",
                    "transaction_id": txn,
                    "cfx_handle": cfx_handle,
                    "source_mode": "cfx",
                })
            materials = data.get("materials") or data.get("installed") or []
            n = 0
            for m in materials:
                if not isinstance(m, dict):
                    continue
                Line.create({
                    "trac_id": header.id,
                    "position": m.get("position") or 0,
                    "mark": m.get("designator") or m.get("mark") or "",
                    "dummy_product_barcode": m.get("part_number")
                    or m.get("barcode") or "",
                    "dummy_product_name": m.get("part_name") or "",
                    "dummy_feeder_barcode": m.get("feeder") or "",
                    "dummy_location_id": m.get("slot") or "",
                    "dummy_lot_name": m.get("lot") or m.get("batch") or "",
                    "dummy_package_code": m.get("reel") or "",
                })
                n += 1
            return {"persisted": True, "trac_id": header.id,
                    "role": "materials", "lines": n}

        # Друго CFX съобщение за europlacer → само station_state update.
        if header and data.get("state"):
            header.station_state = data["state"]
        return {"persisted": bool(header), "role": "noop"}

    def _ingest_parmi(self, env, proxy, event):
        """PARMI SPI/AOI → inspection/measurement статистики."""
        return self._write_generic_stat(env, proxy, event, "parmi")

    def _ingest_oven(self, env, proxy, event):
        """Reflow oven → thermal-profile статистики."""
        return self._write_generic_stat(env, proxy, event, "oven")

    def _ingest_laser(self, env, proxy, event):
        """Laser marking/cutting → laser статистики."""
        return self._write_generic_stat(env, proxy, event, "laser")

    def _ingest_generic(self, env, proxy, event):
        """Fallback за непознат machine_kind."""
        return self._write_generic_stat(env, proxy, event, "generic")

    # ─── Helpers ──────────────────────────────────────────────────
    def _write_generic_stat(self, env, proxy, event, kind):
        """Запиши cfx.machine.stat ред за non-europlacer машина.

        Ако има регистриран extractor за това CFX съобщение (напр. AOI/SPI
        UnitsInspected), той вади реалните данни от `data` в структуриран
        вид → summary полета + вложени cfx.inspection.* редове. Иначе
        падаме на повърхностно best-effort извличане (заварено поведение).
        """
        data = event.get("data") or {}
        message_name = event.get("message_name") or ""
        endpoint = env["cfx.endpoint"].sudo().search([
            ("proxy_id", "=", proxy.id),
            ("cfx_handle", "=", event.get("cfx_handle") or ""),
        ], limit=1)

        vals = {
            "proxy_id": proxy.id,
            "endpoint_id": endpoint.id if endpoint else False,
            "machine_kind": kind,
            "cfx_handle": event.get("cfx_handle") or "",
            "message_name": message_name,
            "transaction_id": event.get("transaction_id") or "",
            "workorder_ref": self._wo_key(event) or "",
            "event_time": self._parse_dt(event.get("ts")) or False,
            "payload_json": json.dumps(data, ensure_ascii=False),
            # Заварени best-effort скалари (extractor-ът ги презаписва).
            "quantity": data.get("quantity") or data.get("qty") or 0.0,
            "defect_count": data.get("defects") or data.get("defect_count") or 0,
            "measured_value": data.get("value") or data.get("measured") or 0.0,
            "unit": data.get("unit") or "",
        }

        # ── Extractor-плъг: реалните данни от CFX message-а ──
        result = extract(message_name, data)
        n_units = n_defects = n_meas = 0
        if result is not None:
            vals.update(result.summary)
            unit_cmds = []
            for u in result.units:
                defects = u.pop("defects", [])
                meas = u.pop("measurements", [])
                n_defects += len(defects)
                n_meas += len(meas)
                unit_cmds.append((0, 0, {
                    **u,
                    "defect_ids": [(0, 0, d) for d in defects],
                    "measurement_ids": [(0, 0, m) for m in meas],
                }))
            if unit_cmds:
                vals["unit_ids"] = unit_cmds
                n_units = len(unit_cmds)

        stat = env["cfx.machine.stat"].sudo().create(vals)
        _logger.info(
            "cfx/ingest %s: stat #%s (%s / %s) — units=%s defects=%s meas=%s",
            kind, stat.id, message_name, event.get("cfx_handle"),
            n_units, n_defects, n_meas)
        return {"persisted": True, "stat_id": stat.id,
                "units": n_units, "defects": n_defects, "measurements": n_meas}

    def _parse_dt(self, raw):
        """ISO-8601 → naive UTC datetime (Odoo-friendly), best-effort."""
        if not raw:
            return None
        try:
            txt = str(raw).replace("Z", "+00:00")
            dt = datetime.fromisoformat(txt)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except (ValueError, TypeError):
            return None
