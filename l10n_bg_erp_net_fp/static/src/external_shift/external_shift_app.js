/** @odoo-module **/

import { Component, mount, whenReady, xml } from "@odoo/owl";
import { getTemplate } from "@web/core/templates";

// Step 1 — services (worked).
import "@l10n_bg_erp_net_fp/external_shift/services/device_proxy_service";
import "@l10n_bg_erp_net_fp/external_shift/services/shift_state_service";

// Step 2 — sub-component imports.
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
                    Step 2 — sub-components imported (not used yet).
                </p>
            </div>
        </div>
    `;
    static components = { TopBar, ProductsGrid, LiveFeed };
    static props = {};
}


(async function _start() {
    try {
        await whenReady();
        const root = document.getElementById("external_shift_root");
        if (root) {
            root.innerHTML = "";
        }
        await mount(ExternalShiftApp, root || document.body, {
            getTemplate,
            dev: true,
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
