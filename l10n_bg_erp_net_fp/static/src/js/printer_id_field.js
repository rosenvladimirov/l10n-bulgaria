/** @odoo-module **/

/**
 * `printer_id_select` — char-field widget that auto-discovers
 * available printers from the Odoo.ErpNet.FP proxy and renders
 * a <select> dropdown. Falls back to a plain <input> if the proxy
 * is unreachable, returns an empty list, or the host is blank.
 *
 * Used on fiscal.printer.device.printer_id. Reads the sibling
 * `host` and `ssl_verify` fields from the record to know which
 * proxy to query.
 *
 * Discovery strategy:
 *   1. Browser-side fetch first (works for browser-proxy mode where
 *      the proxy URL is local — e.g. `https://erpnet.local/` —
 *      reachable from the cashier's browser but NOT from the Odoo
 *      server). CORS must be enabled on the proxy.
 *   2. On any failure (CORS, DNS, TLS), fall back to the ORM call
 *      `list_proxy_printers` — works for direct-mode setups where
 *      the Odoo server itself can reach the proxy.
 */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CharField, charField } from "@web/views/fields/char/char_field";

import { onWillStart, useState } from "@odoo/owl";

export class PrinterIdSelectField extends CharField {
    static template = "l10n_bg_erp_net_fp.PrinterIdSelectField";

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

    _normalizeChoices(data) {
        const out = [];
        if (data && typeof data === "object") {
            for (const [pid, info] of Object.entries(data)) {
                const i = info || {};
                out.push({
                    id: pid,
                    label: `${pid} — ${i.model || i.manufacturer || "?"}`,
                    uri: i.uri || "",
                    model: i.model || "",
                });
            }
        }
        return out;
    }

    async _fetchFromBrowser(host) {
        // Direct browser fetch — works when the proxy is on the
        // cashier's network (e.g. `https://erpnet.local/`).
        // Requires CORS-enabled proxy (Odoo.ErpNet.FP enables it
        // by default via Traefik dynamic config).
        const url = host.replace(/\/+$/, "") + "/printers";
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

    async _fetchFromServer(host) {
        // Fallback — Odoo server makes the request. Useful in
        // direct-mode setups (Odoo server has line-of-sight to
        // the proxy).
        const r = await this.orm.call(
            "fiscal.printer.device",
            "list_proxy_printers",
            [],
            {
                host,
                ssl_verify: this.props.record.data.ssl_verify || false,
            },
        );
        if (!r || !r.ok) {
            throw new Error((r && r.message) || _t("unknown error"));
        }
        // Server returns already-normalized list
        return r.printers || [];
    }

    async loadChoices() {
        const host = this.props.record.data.host;
        if (!host) {
            this.state.choices = [];
            return;
        }
        this.state.loading = true;
        this.state.errored = false;
        let browserErr = null;
        try {
            // 1) browser-side first
            const data = await this._fetchFromBrowser(host);
            this.state.choices = this._normalizeChoices(data);
            return;
        } catch (e) {
            browserErr = e;
            // continue to fallback
        }
        try {
            // 2) ORM fallback (server-side)
            const fromServer = await this._fetchFromServer(host);
            // _fetchFromServer returns already-formatted [{id,label,...}]
            this.state.choices = Array.isArray(fromServer)
                ? fromServer
                : this._normalizeChoices(fromServer);
        } catch (e2) {
            this.state.choices = [];
            this.state.errored = true;
            this.state.errorMessage = `${browserErr && browserErr.message
                ? "browser: " + browserErr.message + "; "
                : ""}server: ${e2.message || String(e2)}`;
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
                _t("Found %s printer(s) on the proxy.", this.state.choices.length),
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

registry.category("fields").add("printer_id_select", {
    ...charField,
    component: PrinterIdSelectField,
});
