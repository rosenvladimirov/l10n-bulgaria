/** @odoo-module **/

import { Component } from "@odoo/owl";
import { ShiftStatusBadge } from
    "@l10n_bg_erp_net_fp/external_shift/components/shift_status_badge/shift_status_badge";


export class TopBar extends Component {
    static template = "l10n_bg_erp_net_fp.ExternalShift.TopBar";
    static components = { ShiftStatusBadge };
    static props = {
        devices: { type: Array },
        deviceId: { type: [Number, Boolean] },
        shift: { type: [Object, null] },
        busy: { type: Object },
        onDeviceChange: { type: Function },
        onOpenShift: { type: Function },
        onCloseShift: { type: Function },
        onXReport: { type: Function },
        onZReport: { type: Function },
        onRefresh: { type: Function },
        onClose: { type: Function },
    };

    get state() {
        return this.props.shift ? this.props.shift.state : "draft";
    }

    get canOpen() {
        return !this.props.shift
            || ["closed", "draft", "error"].includes(this.state);
    }
    get canClose() {
        return this.props.shift
            && ["open", "error"].includes(this.state);
    }
    get canFireReport() {
        return this.props.shift && this.state === "open";
    }

    onDeviceChangeHandler(ev) {
        const id = parseInt(ev.target.value, 10) || false;
        this.props.onDeviceChange(id);
    }
}
