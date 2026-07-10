/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { patch } from "@web/core/utils/patch";
import { useBus } from "@web/core/utils/hooks";
import { onWillUnmount } from "@odoo/owl";
import { SpreadsheetDashboardAction } from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_action";
import { Status } from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_loader_service";

// Мостът ("плъгът"): при нов CFX запис презарежда данните на активния
// дашборд БЕЗ пълен refresh на страницата. Odoo Spreadsheet дашбордите
// зареждат pivot/list данните веднъж при отваряне; тук ги пре-оценяваме
// чрез командата REFRESH_ALL_DATA_SOURCES на o-spreadsheet модела
// (pivot_odoo_ui_plugin / list_core_view_plugin я хващат и рефрешват
// всички pivot-и и списъци, след което данните се пре-оценяват).
//
// Debounce: CFX трафикът може да е плътен (десетки съобщения/сек). Пълно
// пре-fetch-ване на всеки запис би залято сървъра, затова trailing debounce
// групира вълните в най-много едно освежаване на CFX_REFRESH_DEBOUNCE_MS.
const CFX_REFRESH_DEBOUNCE_MS = 2000;

patch(SpreadsheetDashboardAction.prototype, {
    setup() {
        super.setup();
        this._cfxRefreshTimer = null;
        // Слушаме глобалното env.bus събитие, което cfx_dashboard_bus.js
        // излъчва при broadcast от сървъра. useBus се чисти при unmount.
        useBus(this.env.bus, "CFX_STAT_NEW", () => this._scheduleCfxRefresh());
        onWillUnmount(() => {
            if (this._cfxRefreshTimer) {
                clearTimeout(this._cfxRefreshTimer);
                this._cfxRefreshTimer = null;
            }
        });
    },

    /** Trailing debounce — едно освежаване на вълна CFX съобщения. */
    _scheduleCfxRefresh() {
        if (this._cfxRefreshTimer) {
            return;
        }
        this._cfxRefreshTimer = setTimeout(() => {
            this._cfxRefreshTimer = null;
            this._refreshCfxDashboard();
        }, CFX_REFRESH_DEBOUNCE_MS);
    },

    /** Пре-оценява pivot-ите/списъка на активния дашборд. */
    _refreshCfxDashboard() {
        const dashboard = this.loader.getActiveDashboard();
        if (dashboard && dashboard.status === Status.Loaded && dashboard.model) {
            dashboard.model.dispatch("REFRESH_ALL_DATA_SOURCES");
        }
    },
});
