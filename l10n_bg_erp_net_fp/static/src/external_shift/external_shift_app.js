/** @odoo-module **/

import { Component, mount, whenReady, xml } from "@odoo/owl";
import { getTemplate } from "@web/core/templates";


// Minimal smoke-test app — no env, no services, no useService, no
// imported sub-components. If this mounts, the bundle infrastructure
// is OK and the previous "class constructors must be invoked with
// 'new'" error came from our service/component imports. If it still
// fails, something in the bundle includes itself is broken.
class ExternalShiftApp extends Component {
    static template = xml`
        <div class="d-flex align-items-center justify-content-center vh-100"
             style="background:#f4f4f4;">
            <div class="text-center p-4 bg-white rounded shadow-sm">
                <h2>External Shift Dashboard</h2>
                <p class="text-muted mb-0">
                    Phase 0 boot smoke-test — if you see this, OWL mounted.
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
