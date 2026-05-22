/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { registry } from "@web/core/registry";

/**
 * Central live-refresh + proxy-event hub.  One service that absorbs:
 *
 *   live_refresh/record  -> env.bus event "LIVE_REFRESH"
 *   live_refresh/field   -> env.bus event "LIVE_REFRESH_FIELD"
 *   live_refresh/list    -> env.bus event "LIVE_REFRESH_LIST"
 *   erpnet_fp_fleet      -> env.bus event "FLEET_UPDATE"   (was fleet_autorefresh.js)
 *   erpnet_fp_proxy_events -> env.bus event "PROXY_EVENT"  (new — bus_inject envelope)
 *
 * Plugin modules subscribe via env.bus.addEventListener("PROXY_EVENT", cb)
 * where cb receives a CustomEvent whose `.detail` is the full envelope
 * { v, type, source, ts, id, data }. To filter, switch on `detail.type`
 * (a string like "plate.detected" / "door.opened") inside the handler.
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
};

function _formatProxyEvent(envelope) {
    const {type, source = {}, data = {}} = envelope || {};
    const meta = _TOAST_KIND[type] || {kind: "info", title: type};
    const parts = [];
    if (source.proxy) parts.push(source.proxy);
    if (source.device) parts.push(source.device);
    // Pick a couple of recognisable data fields if present.
    if (data.plate) parts.push(`plate=${data.plate}`);
    if (data.card_id) parts.push(`card=${data.card_id}`);
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
            try {
                const t = _formatProxyEvent(payload);
                notification.add(t.message, {
                    title: t.title,
                    type: t.kind,
                    sticky: t.sticky,
                });
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
