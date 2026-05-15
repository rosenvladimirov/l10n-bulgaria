/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { registry } from "@web/core/registry";

/**
 * Forwards generic live-refresh bus notifications as env.bus events so
 * patched controllers can react.
 *
 *   live_refresh/record -> LIVE_REFRESH        (full record/list reload)
 *   live_refresh/field  -> LIVE_REFRESH_FIELD  (reload + flash fields)
 *   live_refresh/list   -> LIVE_REFRESH_LIST   (reload + highlight rows)
 */
const liveRefreshService = {
    dependencies: ["bus_service"],

    start(env, { bus_service }) {
        bus_service.subscribe("live_refresh/record", (payload) => {
            env.bus.trigger("LIVE_REFRESH", payload);
        });
        bus_service.subscribe("live_refresh/field", (payload) => {
            env.bus.trigger("LIVE_REFRESH_FIELD", payload);
        });
        bus_service.subscribe("live_refresh/list", (payload) => {
            env.bus.trigger("LIVE_REFRESH_LIST", payload);
        });
    },
};

registry.category("services").add("live_refresh", liveRefreshService);
