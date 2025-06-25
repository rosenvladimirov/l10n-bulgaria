/** @odoo-module **/

import { formatMonetary } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import {
    Component,
    onWillRender,
    toRaw,
} from "@odoo/owl";

class SignedTaxGroup extends Component {
    static template = "l10n_bg_tax_admin.SignedTaxTotals";
    static props = {
        totals: { optional: true },
        subtotal: { optional: true },
        taxGroup: { optional: true },
    };
}

export class SignedTaxTotalsComponent extends Component {
    static template = "l10n_bg_tax_admin.SignedTaxTotalsField";
    static components = { SignedTaxGroup };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.totals = {};
        this.formatData(this.props);
        onWillRender(() => this.formatData(this.props));
    }

    formatMonetary(value) {
        return formatMonetary(value, {
            currencyId: this.totals.currency_id
        });
    }

    formatData(props) {
        let totals = JSON.parse(JSON.stringify(toRaw(props.record.data[this.props.name])));
        if (!totals) {
            return;
        }
        this.totals = totals;
    }
}

export const signedTaxTotalsComponent = {
    component: SignedTaxTotalsComponent,
};

// Регистриране на компонента
registry.category("fields").add("signed-tax-totals", signedTaxTotalsComponent);
