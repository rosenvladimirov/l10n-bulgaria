/** @odoo-module **/

import { Component } from "@odoo/owl";


export class ShiftStatusBadge extends Component {
    static template =
        "l10n_bg_erp_net_fp.ExternalShift.ShiftStatusBadge";
    static props = {
        state: { type: String },
    };

    get badgeClass() {
        return {
            draft:    "text-bg-secondary",
            opening:  "text-bg-warning",
            open:     "text-bg-info",
            closing:  "text-bg-warning",
            closed:   "text-bg-success",
            error:    "text-bg-danger",
        }[this.props.state] || "text-bg-secondary";
    }

    get label() {
        return this.props.state.toUpperCase();
    }
}
