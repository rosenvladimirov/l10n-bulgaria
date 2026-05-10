/** @odoo-module **/

import { Component } from "@odoo/owl";


export class ProductsGrid extends Component {
    static template = "l10n_bg_erp_net_fp.ExternalShift.ProductsGrid";
    static props = {
        products: { type: Array },
        loading: { type: Boolean },
    };

    badgeClass(plu_status) {
        return {
            ok:      "text-bg-success",
            stale:   "text-bg-warning",
            missing: "text-bg-danger",
            error:   "text-bg-danger",
        }[plu_status] || "text-bg-secondary";
    }

    badgeGlyph(plu_status) {
        return {
            ok:      "✓",
            stale:   "⚠",
            missing: "✗",
            error:   "✗",
        }[plu_status] || "?";
    }
}
