/** @odoo-module **/

import { Component } from "@odoo/owl";


export class LiveFeed extends Component {
    static template = "l10n_bg_erp_net_fp.ExternalShift.LiveFeed";
    static props = {
        shift: { type: [Object, null] },
        message: { type: String },
    };
}
