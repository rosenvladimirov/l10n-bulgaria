/** @odoo-module **/

import { Component, mount, useState, whenReady, xml } from "@odoo/owl";
import { getTemplate } from "@web/core/templates";
import { useService } from "@web/core/utils/hooks";
import { makeEnv, startServices } from "@web/env";

// Step 1 — services (worked).
import "@l10n_bg_erp_net_fp/external_shift/services/device_proxy_service";
import "@l10n_bg_erp_net_fp/external_shift/services/shift_state_service";

// Step 2 — sub-components (worked).
import { TopBar } from
    "@l10n_bg_erp_net_fp/external_shift/components/top_bar/top_bar";
import { ProductsGrid } from
    "@l10n_bg_erp_net_fp/external_shift/components/products_grid/products_grid";
import { LiveFeed } from
    "@l10n_bg_erp_net_fp/external_shift/components/live_feed/live_feed";


class ExternalShiftApp extends Component {
    static template = xml`
        <div class="d-flex align-items-center justify-content-center vh-100"
             style="background:#f4f4f4;">
            <div class="text-center p-4 bg-white rounded shadow-sm">
                <h2>External Shift Dashboard</h2>
                <p class="text-muted mb-0">
                    Step 3 — env + services started, useService active.
                </p>
                <p class="small text-muted mb-0">
                    devices: <t t-esc="state.deviceCount"/>
                </p>
            </div>
        </div>
    `;
    static components = { TopBar, ProductsGrid, LiveFeed };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.shiftSvc = useService("l10n_bg_external_shift.shift_state");
        this.state = useState({ deviceCount: "—" });
    }
}


(async function _start() {
    try {
        await whenReady();
        const env = makeEnv();
        await startServices(env);
        const root = document.getElementById("external_shift_root");
        if (root) {
            root.innerHTML = "";
        }
        await mount(ExternalShiftApp, root || document.body, {
            env,
            getTemplate,
            dev: env.debug || true,
        });
    } catch (err) {
        console.error("[ExternalShift] boot failed", err);
        const root = document.getElementById("external_shift_root");
        if (root) {
            root.innerHTML =
                `<div class="alert alert-danger m-4">`
                + `External Shift Dashboard failed to start: `
                + `${err.message || err}</div>`;
        }
    }
})();
