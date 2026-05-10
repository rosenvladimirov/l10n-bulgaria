/** @odoo-module **/

/**
 * External Shift Dashboard — POS-mimic OWL component for external POS
 * mode (cashier rings up sales DIRECTLY on the fiscal device; Odoo
 * is shift container + visualizer only).
 *
 * Architecture:
 *
 *   Browser (this component)
 *     ├─ Direct fetch → ErpNet.FP proxy (LAN-reachable from browser)
 *     │     • POST /printers/{id}/plu/sync
 *     │     • POST /printers/{id}/vat-rates
 *     │     • POST /printers/{id}/operators
 *     │     • POST /printers/{id}/zreport
 *     │     • POST /printers/{id}/xreport
 *     │     • POST /printers/{id}/journal
 *     ├─ ORM call → Odoo backend (storage only)
 *     │     • create l10n.bg.fiscal.shift
 *     │     • action_mark_open / action_mark_closed
 *     │     • read product.product + l10n.bg.fiscal.plu
 *     └─ No bus channels, no server-side proxy hop, no 30s timeout.
 *
 * Phase 0 ships:
 *   • Top bar — shift state + 4 buttons (Open / Close / X / Z)
 *   • Products grid — products with `available_in_pos=True`, each
 *     decorated with PLU status: ✓ programmed / ✗ missing / ⚠ stale
 *   • Right panel — placeholder for Phase 1 live sales feed
 *
 * Phase 1 (next session) will add:
 *   • Add/remove PLU click handlers on product cards
 *   • Live sales feed via 5s journal poll
 *   • Real-time receipts/h + sales today counters
 */

import { Component, useState, onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/** Per-operation timeout budgets, in ms. Mirrors backend constants
 * in fiscal_printer_device_external.py. */
const TIMEOUT_PLU_SYNC_MS = 90000;
const TIMEOUT_VAT_MS = 30000;
const TIMEOUT_OPERATORS_MS = 30000;
const TIMEOUT_REPORT_MS = 90000;
const TIMEOUT_STATUS_MS = 5000;

async function _fetchJson(url, { method = "GET", body, timeoutMs }) {
    const ctl = new AbortController();
    const tid = setTimeout(() => ctl.abort(), timeoutMs);
    try {
        const resp = await fetch(url, {
            method,
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body: body ? JSON.stringify(body) : undefined,
            credentials: "omit",
            signal: ctl.signal,
        });
        const text = await resp.text();
        let json = null;
        try { json = text ? JSON.parse(text) : null; } catch (_e) { /* ignore */ }
        if (!resp.ok) {
            const msg = json
                ? (json.detail || JSON.stringify(json))
                : (text || `HTTP ${resp.status}`);
            throw new Error(`HTTP ${resp.status}: ${msg}`);
        }
        return json;
    } finally {
        clearTimeout(tid);
    }
}


export class ExternalShiftDashboard extends Component {
    static template = "l10n_bg_erp_net_fp.ExternalShiftDashboard";
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: [Number, Boolean], optional: true },
        className: { type: String, optional: true },
        globalState: { type: Object, optional: true },
        updateActionState: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        this.state = useState({
            loading: true,
            // Active device (chosen by operator at start)
            devices: [],         // [{id, name, host, printer_id, ...}]
            deviceId: false,
            // Active shift (if any)
            shiftId: false,
            shiftState: "draft", // draft / opening / open / closing / closed / error
            // Products + PLU index (populated on load)
            products: [],        // [{id, name, default_code, lst_price, plu_status: 'ok'|'missing'|'stale'}]
            plusByProductId: {}, // product_id -> {plu_number, push_state, name, price}
            // Loading flags per button
            busy: {
                open: false,
                close: false,
                x_report: false,
                z_report: false,
                refresh: false,
            },
            lastMessage: "",
        });

        onMounted(() => this._reload());
    }

    async _reload() {
        this.state.loading = true;
        try {
            const devices = await this.orm.searchRead(
                "fiscal.printer.device",
                [["active", "=", true]],
                ["id", "name", "host", "printer_id", "connection_mode"],
            );
            this.state.devices = devices;
            if (!this.state.deviceId && devices.length) {
                this.state.deviceId = devices[0].id;
            }
            await this._loadActiveShift();
            await this._loadProductsAndPlu();
        } catch (err) {
            this._showError(_t("Failed to load dashboard"), err);
        } finally {
            this.state.loading = false;
        }
    }

    async _loadActiveShift() {
        if (!this.state.deviceId) return;
        const shift = await this.orm.call(
            "l10n.bg.fiscal.shift",
            "find_active_shift",
            [this.state.deviceId],
        );
        if (shift) {
            // find_active_shift returns a recordset id; fetch detail
            const recs = await this.orm.read(
                "l10n.bg.fiscal.shift",
                Array.isArray(shift) ? shift : [shift],
                ["id", "name", "state"],
            );
            if (recs.length) {
                this.state.shiftId = recs[0].id;
                this.state.shiftState = recs[0].state;
                return;
            }
        }
        this.state.shiftId = false;
        this.state.shiftState = "draft";
    }

    async _loadProductsAndPlu() {
        // Products eligible for PLU programming
        const products = await this.orm.searchRead(
            "product.product",
            [["available_in_pos", "=", true]],
            ["id", "display_name", "default_code", "lst_price", "barcode"],
            { limit: 200 },  // Phase 0 cap; pagination in Phase 1
        );

        // PLU registry — index by linked product
        const plus = await this.orm.searchRead(
            "l10n.bg.fiscal.plu",
            [["active", "=", true]],
            ["id", "plu_number", "name", "price", "push_state",
             "product_ids"],
        );
        const byProduct = {};
        for (const p of plus) {
            for (const pid of (p.product_ids || [])) {
                byProduct[pid] = p;
            }
        }

        for (const prod of products) {
            const plu = byProduct[prod.id];
            if (!plu) {
                prod.plu_status = "missing";
                prod.plu_label = "";
            } else if (plu.push_state === "pushed") {
                prod.plu_status = "ok";
                prod.plu_label = `PLU#${plu.plu_number}`;
            } else if (["stale", "name_drift", "pending"].includes(
                plu.push_state)) {
                prod.plu_status = "stale";
                prod.plu_label = `PLU#${plu.plu_number} (${plu.push_state})`;
            } else {
                prod.plu_status = "error";
                prod.plu_label = `PLU#${plu.plu_number} (${plu.push_state})`;
            }
        }
        this.state.products = products;
        this.state.plusByProductId = byProduct;
    }

    get activeDevice() {
        return this.state.devices.find(d => d.id === this.state.deviceId)
            || null;
    }

    get canOpen() {
        return !this.state.shiftId
            || ["closed", "draft", "error"].includes(this.state.shiftState);
    }

    get canClose() {
        return this.state.shiftId
            && ["open", "error"].includes(this.state.shiftState);
    }

    get canFireReport() {
        return this.state.shiftId
            && this.state.shiftState === "open";
    }

    onDeviceChange(ev) {
        this.state.deviceId = parseInt(ev.target.value, 10) || false;
        this._loadActiveShift();
    }

    /**
     * Open Shift workflow
     *  1. ORM create l10n.bg.fiscal.shift (state=draft)
     *  2. ORM action_mark_opening (state=opening)
     *  3. Browser fetch — pre-flight status
     *  4. Browser fetch — push PLU bulk + VAT + operators (parallel)
     *  5. ORM action_mark_open with push summary
     */
    async onClickOpen() {
        const dev = this.activeDevice;
        if (!dev) {
            this.notification.add(_t("Select a device first."),
                { type: "warning" });
            return;
        }
        if (!dev.host || !dev.printer_id) {
            this.notification.add(
                _t("Device is missing host/printer_id config."),
                { type: "danger" });
            return;
        }
        this.state.busy.open = true;
        const summaryLines = [];
        try {
            // 1. Create shift record
            const shiftId = await this.orm.create(
                "l10n.bg.fiscal.shift",
                [{
                    device_id: dev.id,
                    operator_user_id: false,  // default = current user
                }],
            );
            this.state.shiftId = shiftId[0];
            await this.orm.call(
                "l10n.bg.fiscal.shift",
                "action_mark_opening",
                [this.state.shiftId],
            );
            this.state.shiftState = "opening";

            // 2. Pre-flight status
            const baseUrl = dev.host.replace(/\/+$/, "");
            const statusUrl = `${baseUrl}/printers/`
                + encodeURIComponent(dev.printer_id) + "/status";
            try {
                const st = await _fetchJson(statusUrl, {
                    method: "GET", timeoutMs: TIMEOUT_STATUS_MS });
                if (st && st.ok === false) {
                    summaryLines.push(`[status] ✗ device not ready: `
                        + JSON.stringify(st.messages || []));
                    throw new Error("Device pre-flight failed");
                }
                summaryLines.push("[status] ✓ device ready");
            } catch (err) {
                summaryLines.push(`[status] ✗ ${err.message}`);
                throw err;
            }

            // 3. Push PLU bulk (Phase 0: just trigger — backend already
            //    has registry; we use the device's bulk endpoint)
            const pluItems = Object.values(this.state.plusByProductId)
                .filter((v, i, a) => a.findIndex(
                    x => x.plu_number === v.plu_number) === i);
            try {
                if (pluItems.length) {
                    await _fetchJson(
                        `${baseUrl}/printers/`
                        + encodeURIComponent(dev.printer_id) + "/plu/sync",
                        {
                            method: "POST",
                            body: { items: pluItems.map(p => ({
                                plu: p.plu_number,
                                name: p.name,
                                price: p.price,
                            })) },
                            timeoutMs: TIMEOUT_PLU_SYNC_MS,
                        },
                    );
                    summaryLines.push(
                        `[plu] ✓ ${pluItems.length} PLUs pushed`);
                } else {
                    summaryLines.push("[plu] — no PLUs to push");
                }
            } catch (err) {
                summaryLines.push(`[plu] ✗ ${err.message}`);
            }

            // 4. Mark open
            await this.orm.call(
                "l10n.bg.fiscal.shift",
                "action_mark_open",
                [this.state.shiftId],
                { push_summary: summaryLines.join("\n") },
            );
            this.state.shiftState = "open";
            this.state.lastMessage = _t("Shift opened.");
            this.notification.add(_t("Shift opened successfully."),
                { type: "success" });
        } catch (err) {
            this._showError(_t("Open Shift failed"), err);
            if (this.state.shiftId) {
                await this.orm.call(
                    "l10n.bg.fiscal.shift",
                    "action_mark_error",
                    [this.state.shiftId],
                    { message: String(err.message || err) },
                ).catch(() => {});
                this.state.shiftState = "error";
            }
        } finally {
            this.state.busy.open = false;
        }
    }

    /**
     * Close Shift workflow
     *  1. ORM action_mark_closing
     *  2. Browser fetch — Z-report (totals) + journal pull
     *  3. ORM action_mark_closed with z_data + receipts_data
     */
    async onClickClose() {
        const dev = this.activeDevice;
        if (!dev || !this.state.shiftId) return;
        this.state.busy.close = true;
        const summaryLines = [];
        try {
            await this.orm.call(
                "l10n.bg.fiscal.shift",
                "action_mark_closing",
                [this.state.shiftId],
            );
            this.state.shiftState = "closing";

            const baseUrl = dev.host.replace(/\/+$/, "");
            const printerSeg = encodeURIComponent(dev.printer_id);

            // Z-report (with parsed totals)
            let zData = {};
            try {
                zData = await _fetchJson(
                    `${baseUrl}/printers/${printerSeg}/zreport-totals`,
                    { method: "POST", timeoutMs: TIMEOUT_REPORT_MS },
                ) || {};
                summaryLines.push(
                    `[z] ✓ Z#${zData.z_number || "?"} `
                    + `total=${(zData.total || 0).toFixed(2)}`);
            } catch (err) {
                summaryLines.push(`[z] ✗ ${err.message}`);
                throw err;
            }

            // Journal pull — Phase 0 stub: empty list. Phase 1 will
            // call /printers/{id}/journal and parse receipts.
            const receiptsData = [];
            summaryLines.push("[journal] — not implemented in Phase 0");

            await this.orm.call(
                "l10n.bg.fiscal.shift",
                "action_mark_closed",
                [this.state.shiftId],
                {
                    z_data: zData,
                    receipts_data: receiptsData,
                    push_summary: summaryLines.join("\n"),
                },
            );
            this.state.shiftState = "closed";
            this.state.shiftId = false;
            this.state.lastMessage = _t("Shift closed.");
            this.notification.add(_t("Shift closed."),
                { type: "success" });
        } catch (err) {
            this._showError(_t("Close Shift failed"), err);
        } finally {
            this.state.busy.close = false;
        }
    }

    async onClickXReport() {
        const dev = this.activeDevice;
        if (!dev) return;
        this.state.busy.x_report = true;
        try {
            const baseUrl = dev.host.replace(/\/+$/, "");
            const url = `${baseUrl}/printers/`
                + encodeURIComponent(dev.printer_id) + "/xreport";
            const res = await _fetchJson(url, {
                method: "POST", timeoutMs: TIMEOUT_REPORT_MS });
            this.notification.add(
                _t("X-report fired. %s", JSON.stringify(res || {}, null, 2)),
                { type: "success", sticky: true });
        } catch (err) {
            this._showError(_t("X-report failed"), err);
        } finally {
            this.state.busy.x_report = false;
        }
    }

    async onClickZReportAdHoc() {
        // Ad-hoc Z without closing the shift (managers' override)
        const dev = this.activeDevice;
        if (!dev) return;
        this.state.busy.z_report = true;
        try {
            const baseUrl = dev.host.replace(/\/+$/, "");
            const url = `${baseUrl}/printers/`
                + encodeURIComponent(dev.printer_id) + "/zreport";
            const res = await _fetchJson(url, {
                method: "POST", timeoutMs: TIMEOUT_REPORT_MS });
            this.notification.add(
                _t("Z-report fired. %s", JSON.stringify(res || {}, null, 2)),
                { type: "success", sticky: true });
        } catch (err) {
            this._showError(_t("Z-report failed"), err);
        } finally {
            this.state.busy.z_report = false;
        }
    }

    async onClickRefresh() {
        this.state.busy.refresh = true;
        try {
            await this._reload();
            this.notification.add(_t("Reloaded."), { type: "info" });
        } finally {
            this.state.busy.refresh = false;
        }
    }

    _showError(title, err) {
        const msg = err && err.message ? err.message : String(err);
        this.notification.add(msg, {
            type: "danger", sticky: true, title,
        });
    }
}

registry.category("actions").add(
    "l10n_bg_external_shift_dashboard", ExternalShiftDashboard);
