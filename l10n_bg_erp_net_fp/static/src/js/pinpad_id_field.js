/** @odoo-module **/

/**
 * `pinpad_id_select` — char-field widget that auto-discovers the
 * pinpads registered on the Odoo.ErpNet.FP proxy and renders a
 * <select> dropdown. Mirrors `printer_id_select` (printer_id_field.js)
 * but lists `/pinpads` instead of `/printers`.
 *
 * Used on pos.payment.method.l10n_bg_pinpad_id. The payment-method form
 * has NO `host` field of its own, so the proxy host is resolved via the
 * ORM helper `pos.payment.method.l10n_bg_list_pinpads` (it reads the
 * configured fiscal.printer.device host). Discovery strategy:
 *   1. ORM call → returns {host, pinpads(server-side attempt)}. In
 *      browser-proxy mode the Odoo server cannot reach the local proxy,
 *      so the server list usually fails — but it still gives us the host.
 *   2. Browser-side fetch `<host>/pinpads` (the cashier's browser CAN
 *      reach the local proxy; CORS enabled on the proxy). Preferred.
 *   3. Fall back to the server list if the browser fetch fails.
 */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CharField, charField } from "@web/views/fields/char/char_field";

import { onWillStart, useState } from "@odoo/owl";

export class PinpadIdSelectField extends CharField {
    static template = "l10n_bg_erp_net_fp.PinpadIdSelectField";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            choices: [],
            loading: false,
            errored: false,
            errorMessage: "",
        });
        onWillStart(() => this.loadChoices());
    }

    _normalize(data) {
        const out = [];
        if (data && typeof data === "object") {
            for (const [pid, info] of Object.entries(data)) {
                const i = info || {};
                out.push({
                    id: pid,
                    label: `${pid} — ${i.model || i.driver || "?"}`,
                });
            }
        }
        return out;
    }

    async _fetchFromBrowser(host) {
        const url = host.replace(/\/+$/, "") + "/pinpads";
        const r = await fetch(url, {
            method: "GET",
            credentials: "omit",
            headers: { Accept: "application/json" },
        });
        if (!r.ok) {
            throw new Error(`HTTP ${r.status}`);
        }
        return await r.json();
    }

    async loadChoices() {
        this.state.loading = true;
        this.state.errored = false;
        let host = "";
        let serverChoices = [];
        // 1) ORM helper — host source (+ server-side list attempt)
        try {
            const res = await this.orm.call(
                "pos.payment.method", "l10n_bg_list_pinpads", [],
            );
            host = (res && res.host) || "";
            if (res && res.ok && Array.isArray(res.pinpads)) {
                serverChoices = res.pinpads;
            }
        } catch (e) {
            // ignore — try whatever host we have (none)
        }
        if (!host) {
            this.state.choices = serverChoices;
            this.state.loading = false;
            if (!serverChoices.length) {
                this.state.errored = true;
                this.state.errorMessage = _t("No fiscal device / proxy host configured.");
            }
            return;
        }
        // 2) browser-side fetch (browser-proxy mode) — preferred
        try {
            const data = await this._fetchFromBrowser(host);
            this.state.choices = this._normalize(data);
        } catch (e) {
            // 3) fall back to the server-side list
            if (serverChoices.length) {
                this.state.choices = serverChoices;
            } else {
                this.state.choices = [];
                this.state.errored = true;
                this.state.errorMessage = e.message || String(e);
            }
        } finally {
            this.state.loading = false;
        }
    }

    onChangeSelect(ev) {
        this.props.record.update({ [this.props.name]: ev.target.value });
    }

    async onClickRefresh() {
        await this.loadChoices();
        if (this.state.errored) {
            this.notification.add(
                _t("Could not reach proxy: %s", this.state.errorMessage),
                { type: "warning" },
            );
        } else {
            this.notification.add(
                _t("Found %s pinpad(s) on the proxy.", this.state.choices.length),
                { type: "success" },
            );
        }
    }

    get currentValue() {
        return this.props.record.data[this.props.name] || "";
    }

    get hasChoices() {
        return this.state.choices.length > 0;
    }
}

registry.category("fields").add("pinpad_id_select", {
    ...charField,
    component: PinpadIdSelectField,
});
