/** @odoo-module **/

/**
 * Client action `l10n_bg_erp_net_fp_grafana_dashboard` — renders the
 * configured Grafana dashboard inside the Odoo backend as a full-
 * height iframe.
 *
 * Reads two ir.config_parameter values via RPC at mount time:
 *   l10n_bg_erp_net_fp.grafana_url            — base URL (no trailing /)
 *   l10n_bg_erp_net_fp.grafana_dashboard_uid  — dashboard UID
 *
 * Builds the iframe URL with kiosk + dark-theme + auto-refresh:
 *   {base}/d/{uid}/?orgId=1&refresh=10s&theme=dark&kiosk=tv
 *
 * Requires Grafana running with GF_SECURITY_ALLOW_EMBEDDING=true,
 * otherwise the iframe stays blank (X-Frame-Options: DENY).
 */

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";


export class GrafanaDashboard extends Component {
    static template = "l10n_bg_erp_net_fp.GrafanaDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({ url: null, error: null });
        onWillStart(async () => {
            try {
                const params = await this.orm.call(
                    "ir.config_parameter", "get_params",
                    [[
                        "l10n_bg_erp_net_fp.grafana_url",
                        "l10n_bg_erp_net_fp.grafana_dashboard_uid",
                    ]]
                ).catch(() => null);
                // Fallback: get one-by-one if get_params isn't available
                let baseUrl, uid;
                if (params && Array.isArray(params)) {
                    baseUrl = params[0];
                    uid = params[1];
                } else {
                    baseUrl = await this.orm.call(
                        "ir.config_parameter", "get_param",
                        ["l10n_bg_erp_net_fp.grafana_url"]
                    );
                    uid = await this.orm.call(
                        "ir.config_parameter", "get_param",
                        ["l10n_bg_erp_net_fp.grafana_dashboard_uid"]
                    );
                }
                if (!baseUrl) {
                    this.state.error = _t(
                        "Grafana base URL not configured. " +
                        "Settings → POS → ErpNet.FP → Grafana base URL."
                    );
                    return;
                }
                if (!uid) uid = "erpnet-fp-overview";
                this.state.url = `${baseUrl.replace(/\/+$/, "")}/d/${uid}/?orgId=1&refresh=10s&theme=dark&kiosk=tv`;
            } catch (e) {
                this.state.error = String(e);
            }
        });
    }
}

registry.category("actions").add(
    "l10n_bg_erp_net_fp_grafana_dashboard",
    GrafanaDashboard,
);
