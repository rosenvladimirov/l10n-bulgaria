/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import { registry } from "@web/core/registry";
import { session } from "@web/session";

/**
 * Central live-refresh + proxy-event hub.  One service that absorbs:
 *
 *   live_refresh/record  -> env.bus event "LIVE_REFRESH"
 *   live_refresh/field   -> env.bus event "LIVE_REFRESH_FIELD"
 *   live_refresh/list    -> env.bus event "LIVE_REFRESH_LIST"
 *   erpnet_fp_fleet      -> env.bus event "FLEET_UPDATE"   (was fleet_autorefresh.js)
 *   erpnet_fp_proxy_events -> env.bus event "PROXY_EVENT"  (bus_inject envelope)
 *
 * On every PROXY_EVENT we also re-fire a typed env.bus event for
 * the common POS-hardware streams so widgets/handlers can subscribe
 * narrowly without switching on `detail.type`:
 *
 *   type == "barcode.scanned" -> env.bus event "BARCODE_SCANNED"
 *   type == "scale.weighed"   -> env.bus event "SCALE_READ"
 *
 * `.detail` of every event is the full envelope
 * `{ v, type, source, ts, id, data }`. For barcode, `data.barcode`
 * (+ optional `symbology`, `reader_id`) carries the scan. For
 * scale, `data.weight` + `data.unit` (default "kg") + `data.stable`
 * (bool) carry the reading.
 *
 * Plugin modules subscribe via:
 *   env.bus.addEventListener("BARCODE_SCANNED", (ev) => {
 *       const code = ev.detail.data.barcode;
 *       ...
 *   });
 *
 * Backwards-compat note: any module that still ships its own
 * `bus_service.addChannel("erpnet_fp_fleet")` + listener will continue
 * to work — bus_service multiplexes subscribers — but the recommended
 * path is the env.bus event above.
 */
// Per-event-type → toast notification class. Maps the proxy_push_schema
// type vocabulary onto Odoo notification kinds + a short headline.
const _TOAST_KIND = {
    "door.opened":    {kind: "success", title: "🚪 Door opened"},
    "door.denied":    {kind: "danger",  title: "🚫 Access denied"},
    "door.sensor":    {kind: "info",    title: "Door state"},
    "card.read":      {kind: "info",    title: "💳 Card scanned"},
    "plate.detected": {kind: "info",    title: "🚗 Plate seen"},
    "plate.injected": {kind: "info",    title: "🧪 Plate (test)"},
    "button.pressed": {kind: "info",    title: "🔘 Exit button"},
    "barrier.changed": {kind: "info",   title: "🚧 Barrier"},
    "controller.heartbeat":   {kind: "info",    title: "📡 Heartbeat"},
    "controller.unreachable": {kind: "warning", title: "📡 Controller unreachable"},
    // Watchdog liveness transitions (server/watchdog.py). Offline is a
    // RED, STICKY alert that stays on screen until the admin dismisses
    // it; online is a transient green recovery toast.
    "controller.offline": {kind: "danger",  title: "🔴 Controller OFFLINE", sticky: true},
    "controller.online":  {kind: "success", title: "🟢 Controller back online"},
    "mqtt.message":   {kind: "info",    title: "📨 MQTT"},
    "biometric.match": {kind: "success", title: "🧬 Face matched"},
    // POS hardware — barcode reader (HID-over-VSP, USB-CDC, BT-VSP)
    // and electronic scale (Adam, Mettler, Datecs, ...). The proxy
    // emits these on `/readers/<id>/ws` and `/scales/<id>/ws`
    // respectively; bus_inject also re-broadcasts them on the
    // erpnet_fp_proxy_events channel so any open Odoo tab sees them
    // (not just the screen subscribed to the WebSocket).
    "barcode.scanned": {kind: "info",   title: "🏷 Barcode"},
    "scale.weighed":   {kind: "info",   title: "⚖️ Scale"},
};

// Muted event-type prefixes, from `ir.config_parameter`
// `l10n_bg_live_refresh.toast_mute_prefixes` (see models/ir_http.py).
// Machine feeds (CFX, MQTT) travel on the same proxy bus channel as
// operator-facing events but at tens of events per second, and their
// toast body is indistinguishable (`proxy · device`) because the
// machine payload carries none of the fields formatted below. Muting
// suppresses only the toast — the bus events themselves keep flowing,
// so dashboards and Shop Floor are unaffected.
// Empty by default: existing databases keep their current behaviour.
function _mutedPrefixes() {
    const raw = session.l10n_bg_live_refresh_toast_mute;
    return Array.isArray(raw) ? raw : [];
}

function _isToastMuted(type) {
    if (!type) return false;
    return _mutedPrefixes().some((prefix) => String(type).startsWith(prefix));
}

function _formatProxyEvent(envelope) {
    const {type, source = {}, data = {}} = envelope || {};
    if (_isToastMuted(type)) return null;
    const meta = _TOAST_KIND[type] || {kind: "info", title: type};
    const parts = [];
    if (source.proxy) parts.push(source.proxy);
    if (source.device) parts.push(source.device);
    // Pick a couple of recognisable data fields if present.
    if (data.plate) parts.push(`plate=${data.plate}`);
    if (data.card_id) parts.push(`card=${data.card_id}`);
    if (data.barcode) parts.push(`barcode=${data.barcode}`);
    if (data.weight !== undefined && data.weight !== null) {
        const unit = data.unit || "kg";
        const stable = data.stable === false ? " (unstable)" : "";
        parts.push(`${data.weight}${unit}${stable}`);
    }
    if (data.state) parts.push(`state=${data.state}`);
    if (data.reason) parts.push(`reason=${data.reason}`);
    if (data.silent_seconds) parts.push(`silent ${data.silent_seconds}s`);
    // Sticky when the type is flagged sticky OR data.severity == alert.
    const sticky = Boolean(meta.sticky) || data.severity === "alert";
    return {kind: meta.kind, title: meta.title,
            message: parts.join(" · ") || type, sticky};
}

const liveRefreshService = {
    dependencies: ["bus_service", "notification"],

    start(env, { bus_service, notification }) {
        // ─── Legacy live-refresh channels ───────────────────────
        bus_service.subscribe("live_refresh/record", (payload) => {
            env.bus.trigger("LIVE_REFRESH", payload);
        });
        bus_service.subscribe("live_refresh/field", (payload) => {
            env.bus.trigger("LIVE_REFRESH_FIELD", payload);
        });
        bus_service.subscribe("live_refresh/list", (payload) => {
            env.bus.trigger("LIVE_REFRESH_LIST", payload);
        });

        // ─── Fleet updates (absorbs fleet_autorefresh.js) ───────
        bus_service.subscribe("erpnet_fp_fleet", (payload) => {
            env.bus.trigger("FLEET_UPDATE", payload);
        });

        // ─── Registered-client push (channel "l10n-bulgaria") ───
        // l10n_bg_config излъчва {vat, name, ee_vat, ee_payroll} с
        // notification type "l10n_bg.register" на канал "l10n-bulgaria".
        // Odoo 16+ bus API: addChannel(channel) АБОНИРА за канала,
        // subscribe(TYPE, cb) лови notification-ите ПО ТИП. Двете заедно
        // са задължителни — само subscribe(channel) НЕ работи. Пре-фирваме
        // като env.bus "L10N_BG_REGISTER" за билинг systray мигалката.
        bus_service.addChannel("l10n-bulgaria");
        bus_service.subscribe("l10n_bg.register", (payload) => {
            env.bus.trigger("L10N_BG_REGISTER", payload);
        });

        // ─── Proxy events (bus_inject envelope) ─────────────────
        // payload = { v, type, source, ts, id, data }
        // Routed as a single "PROXY_EVENT" event; handlers switch on
        // `detail.type`. Keeps the bus channel surface minimal — adding
        // a new event type doesn't require a new subscription.
        //
        // ALSO emits a global toast notification with a sensible
        // type→kind mapping (see _TOAST_KIND above). The visible toast
        // is independent of any open view — operators see live events
        // from every Odoo tab without opening a specific dashboard.
        bus_service.subscribe("erpnet_fp_proxy_events", (payload) => {
            env.bus.trigger("PROXY_EVENT", payload);
            // ─── dedicated convenience events ────────────────────
            // Form widgets / form controllers that only care about
            // barcode or weight don't have to switch on detail.type
            // inside a single PROXY_EVENT handler — they subscribe
            // to the typed event directly.
            try {
                const t = payload && payload.type;
                if (t === "barcode.scanned") {
                    env.bus.trigger("BARCODE_SCANNED", payload);
                } else if (t === "scale.weighed") {
                    env.bus.trigger("SCALE_READ", payload);
                }
            } catch (e) {
                console.warn("typed event dispatch suppressed:", e);
            }
            try {
                const t = _formatProxyEvent(payload);
                if (t) {
                    notification.add(t.message, {
                        title: t.title,
                        type: t.kind,
                        sticky: t.sticky,
                    });
                }
            } catch (e) {
                console.warn("PROXY_EVENT toast suppressed:", e);
            }
            // Per-component refresh hints (data._refresh) — declared in
            // the proxy config `refresh:` block. Re-emit them on the
            // legacy field/list channels so open Form/List controllers
            // repaint exactly the declared field/view. The FormController
            // patch matches on {model, match_field, match_value} so no
            // Odoo res_id round-trip is needed.
            try {
                const hints = payload?.data?._refresh;
                if (Array.isArray(hints)) {
                    for (const h of hints) {
                        if (!h || !h.model) continue;
                        if (h.mode === "list") {
                            env.bus.trigger("LIVE_REFRESH_LIST", {model: h.model});
                        } else if (h.field) {
                            env.bus.trigger("LIVE_REFRESH_FIELD", {
                                model: h.model,
                                fields: [h.field],
                                match_field: h.match_field,
                                match_value: h.match_value,
                            });
                        }
                    }
                }
            } catch (e) {
                console.warn("PROXY_EVENT refresh hints suppressed:", e);
            }
        });
    },
};

registry.category("services").add("live_refresh", liveRefreshService);
