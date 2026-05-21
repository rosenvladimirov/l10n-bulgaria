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
const liveRefreshService = {
    dependencies: ["bus_service"],

    start(env, { bus_service }) {
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
        bus_service.subscribe("erpnet_fp_proxy_events", (payload) => {
            env.bus.trigger("PROXY_EVENT", payload);
        });
    },
};

registry.category("services").add("live_refresh", liveRefreshService);
