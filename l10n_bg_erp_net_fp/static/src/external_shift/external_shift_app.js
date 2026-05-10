/** @odoo-module **/

import { Component, useState, onMounted, mount, whenReady } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { TopBar } from
    "@l10n_bg_erp_net_fp/external_shift/components/top_bar/top_bar";
import { ProductsGrid } from
    "@l10n_bg_erp_net_fp/external_shift/components/products_grid/products_grid";
import { LiveFeed } from
    "@l10n_bg_erp_net_fp/external_shift/components/live_feed/live_feed";

import { templates } from "@web/core/assets";
import { MainComponentsContainer } from
    "@web/core/main_components_container";
import { makeEnv, startServices } from "@web/env";


export class ExternalShiftApp extends Component {
    static template = "l10n_bg_erp_net_fp.ExternalShift.App";
    static components = { TopBar, ProductsGrid, LiveFeed,
                          MainComponentsContainer };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.shiftSvc = useService("l10n_bg_external_shift.shift_state");

        this.config = (window.odoo && window.odoo.__externalShiftConfig__)
            || { shift_id: 0, user_id: 0, company_id: 0 };

        this.state = useState({
            loading: true,
            devices: [],
            deviceId: false,
            shift: null,                // active shift record or null
            products: [],
            plusByProduct: {},
            busy: {
                open: false,
                close: false,
                x_report: false,
                z_report: false,
                refresh: false,
            },
            message: "",
        });

        onMounted(() => this._reload());
    }

    async _reload() {
        this.state.loading = true;
        try {
            this.state.devices = await this.shiftSvc.listDevices();
            if (!this.state.deviceId && this.state.devices.length) {
                this.state.deviceId = this.state.devices[0].id;
            }
            // Pre-selected from URL?
            if (this.config.shift_id && !this.state.shift) {
                this.state.shift = await this.shiftSvc.loadShift(
                    this.config.shift_id);
                if (this.state.shift) {
                    this.state.deviceId =
                        this.state.shift.device_id
                            ? this.state.shift.device_id[0]
                            : this.state.deviceId;
                }
            } else {
                this.state.shift = await this.shiftSvc.findActiveShift(
                    this.state.deviceId);
            }
            const { products, plusByProduct } =
                await this.shiftSvc.loadProductsAndPlu();
            this.state.products = products;
            this.state.plusByProduct = plusByProduct;
        } catch (err) {
            this._error(_t("Failed to load dashboard"), err);
        } finally {
            this.state.loading = false;
        }
    }

    get activeDevice() {
        return this.state.devices.find(d => d.id === this.state.deviceId)
            || null;
    }

    async onDeviceChange(deviceId) {
        this.state.deviceId = deviceId;
        this.state.shift = await this.shiftSvc.findActiveShift(deviceId);
    }

    async onOpenShift() {
        const dev = this.activeDevice;
        if (!dev) {
            this.notification.add(_t("Select a device first."),
                { type: "warning" });
            return;
        }
        this.state.busy.open = true;
        try {
            const shift = await this.shiftSvc.openShift(dev);
            this.state.shift = shift;
            this.state.message = _t("Shift opened.");
            this.notification.add(_t("Shift opened successfully."),
                { type: "success" });
        } catch (err) {
            this._error(_t("Open Shift failed"), err);
        } finally {
            this.state.busy.open = false;
        }
    }

    async onCloseShift() {
        const dev = this.activeDevice;
        if (!dev || !this.state.shift) return;
        this.state.busy.close = true;
        try {
            const shift = await this.shiftSvc.closeShift(
                this.state.shift.id, dev);
            this.state.shift = shift && shift.state === "closed"
                ? null : shift;
            this.state.message = _t("Shift closed.");
            this.notification.add(_t("Shift closed."), { type: "success" });
        } catch (err) {
            this._error(_t("Close Shift failed"), err);
        } finally {
            this.state.busy.close = false;
        }
    }

    async onXReport() {
        const dev = this.activeDevice;
        if (!dev) return;
        this.state.busy.x_report = true;
        try {
            const r = await this.shiftSvc.fireXReport(dev);
            this.notification.add(
                _t("X-report fired. %s",
                   JSON.stringify(r || {}, null, 2)),
                { type: "success", sticky: true });
        } catch (err) {
            this._error(_t("X-report failed"), err);
        } finally {
            this.state.busy.x_report = false;
        }
    }

    async onZReport() {
        const dev = this.activeDevice;
        if (!dev) return;
        this.state.busy.z_report = true;
        try {
            const r = await this.shiftSvc.fireZReport(dev);
            this.notification.add(
                _t("Z-report fired. %s",
                   JSON.stringify(r || {}, null, 2)),
                { type: "success", sticky: true });
        } catch (err) {
            this._error(_t("Z-report failed"), err);
        } finally {
            this.state.busy.z_report = false;
        }
    }

    async onRefresh() {
        this.state.busy.refresh = true;
        try {
            await this._reload();
            this.notification.add(_t("Reloaded."), { type: "info" });
        } finally {
            this.state.busy.refresh = false;
        }
    }

    onClose() {
        // Navigate back to backend (closes the standalone app).
        window.location.href = "/odoo";
    }

    _error(title, err) {
        const msg = err && err.message ? err.message : String(err);
        this.notification.add(msg, {
            type: "danger", sticky: true, title,
        });
    }
}


// Boot the app once OWL templates are ready. Pattern matches POS
// (`point_of_sale.app.js`) — replace the loading shell with the
// MainComponentsContainer + ExternalShiftApp.
async function _start() {
    await whenReady();
    const env = makeEnv();
    await startServices(env);
    const root = document.getElementById("external_shift_root");
    if (root) {
        // Clear the loading splash injected by the QWeb shell.
        root.innerHTML = "";
    }
    await mount(ExternalShiftApp, root || document.body, {
        env,
        templates,
        translateFn: env._t || ((s) => s),
        dev: env.debug,
    });
}

_start().catch((err) => {
    console.error("[ExternalShift] boot failed", err);
    const root = document.getElementById("external_shift_root");
    if (root) {
        root.innerHTML =
            `<div class="alert alert-danger m-4">`
            + `External Shift Dashboard failed to start: `
            + `${err.message || err}</div>`;
    }
});
