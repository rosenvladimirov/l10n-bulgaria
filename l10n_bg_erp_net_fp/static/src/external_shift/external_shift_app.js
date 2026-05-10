/** @odoo-module **/

import { Component, mount, whenReady, xml } from "@odoo/owl";
import { getTemplate } from "@web/core/templates";

// Step 1 — pull in services for their side-effect (registry.add()).
// If the page now fails to load with a class-constructor error,
// the issue lives in one of these services. Otherwise it's the
// sub-components.
import "@l10n_bg_erp_net_fp/external_shift/services/device_proxy_service";
import "@l10n_bg_erp_net_fp/external_shift/services/shift_state_service";


class ExternalShiftApp extends Component {
    static template = xml`
        <div class="d-flex align-items-center justify-content-center vh-100"
             style="background:#f4f4f4;">
            <div class="text-center p-4 bg-white rounded shadow-sm">
                <h2>External Shift Dashboard</h2>
                <p class="text-muted mb-0">
                    Step 1 — services imported, no sub-components yet.
                </p>
            </div>
        </div>
    `;
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
