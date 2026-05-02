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

    async loadChoices() {
        const host = this.props.record.data.host;
        if (!host) {
            this.state.choices = [];
            return;
        }
        this.state.loading = true;
        this.state.errored = false;
        try {
            const r = await this.orm.call(
                "fiscal.printer.device",
                "list_proxy_printers",
                [],
                {
                    host,
                    ssl_verify: this.props.record.data.ssl_verify || false,
                }
            );
            if (r && r.ok) {
                this.state.choices = r.printers || [];
            } else {
                this.state.choices = [];
                this.state.errored = true;
                this.state.errorMessage = (r && r.message) || _t("unknown error");
            }
        } catch (err) {
            this.state.choices = [];
            this.state.errored = true;
            this.state.errorMessage = err.message || String(err);
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
