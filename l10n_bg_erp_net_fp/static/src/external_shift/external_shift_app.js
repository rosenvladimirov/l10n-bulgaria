/** @odoo-module **/

import { Component, mount, useState, onMounted, whenReady, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { getTemplate } from "@web/core/templates";
import { useService } from "@web/core/utils/hooks";
import { makeEnv, startServices } from "@web/env";

import "@l10n_bg_erp_net_fp/external_shift/services/device_proxy_service";
import "@l10n_bg_erp_net_fp/external_shift/services/shift_state_service";

import { TopBar } from
    "@l10n_bg_erp_net_fp/external_shift/components/top_bar/top_bar";
import { ProductsGrid } from
    "@l10n_bg_erp_net_fp/external_shift/components/products_grid/products_grid";
import { LiveFeed } from
    "@l10n_bg_erp_net_fp/external_shift/components/live_feed/live_feed";


export class ExternalShiftApp extends Component {
    static template = xml`
        <div class="o_external_shift_dashboard d-flex flex-column h-100">
            <div class="bg-info p-3">
                Step 4c — sub-components stubbed in template.
                Devices: <t t-esc="state.devices.length"/>
            </div>
        </div>
    `;
    static components = { TopBar, ProductsGrid, LiveFeed };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.shiftSvc = useService("l10n_bg_external_shift.shift_state");

        this.state = useState({
            loading: false,
            devices: [],
            deviceId: false,
            shift: null,
            products: [],
            plusByProduct: {},
            busy: {
                open: false, close: false,
                x_report: false, z_report: false, refresh: false,
            },
            message: "",
        });
    }

    // Step 4c: NO other methods for now — handler bindings in template
    // will be undefined, but at least the module should LOAD.
    onDeviceChange() {}
    onOpenShift() {}
    onCloseShift() {}
    onXReport() {}
    onZReport() {}
    onRefresh() {}
    onClose() {}
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
            translateFn: _t,
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
