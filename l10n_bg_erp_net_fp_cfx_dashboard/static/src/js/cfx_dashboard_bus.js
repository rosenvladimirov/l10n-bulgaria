/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { registry } from "@web/core/registry";

/**
 * Постоянна backend услуга: абонира bus канала "cfx_dashboard" и
 * пре-фирва broadcast-а като env.bus събитие "CFX_STAT_NEW".
 *
 * Живее в web.assets_backend (винаги стартира), огледален подход на
 * l10n_bg_live_refresh/live_refresh_service.js. Мостът върху
 * SpreadsheetDashboardAction (в мързеливия o_spreadsheet bundle) слуша
 * env.bus за "CFX_STAT_NEW" — така bus plumbing-ът е разделен от OWL
 * компонента и не зависи от това дали дашбордът е отворен.
 *
 * Сървърът (cfx.machine.stat.create) излъчва:
 *   bus._sendone("cfx_dashboard", "cfx.machine.stat/new", {model, count})
 */
const cfxDashboardBusService = {
    dependencies: ["bus_service"],

    start(env, { bus_service }) {
        bus_service.addChannel("cfx_dashboard");
        bus_service.subscribe("cfx.machine.stat/new", (payload) => {
            env.bus.trigger("CFX_STAT_NEW", payload);
        });
    },
};

registry.category("services").add("cfx_dashboard_bus", cfxDashboardBusService);
