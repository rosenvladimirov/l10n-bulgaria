/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { useService } from "@web/core/utils/hooks";

export class L10nBgUicField extends CharField {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    get showButton() {
        // Показваме бутона само когато:
        // 1. l10n_bg_uic_type е 'bg_uic'
        // 2. vat е попълнен и започва с BG
        const record = this.props.record;
        const uicType = record.data.l10n_bg_uic_type;
        const vat = record.data.vat;

        return (
            uicType === 'bg_uic' &&
            vat &&
            vat.toUpperCase().startsWith('BG') &&
            !this.props.readonly
        );
    }

    async onButtonClick(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        // Извикваме метода action_fetch_from_registry на записа
        await this.props.record.model.orm.call(
            this.props.record.resModel,
            'action_fetch_from_registry',
            [[this.props.record.resId]],
            {}
        ).then((action) => {
            if (action) {
                this.action.doAction(action);
            }
        });
    }
}

L10nBgUicField.template = "l10n_bg_company_registry.L10nBgUicField";

registry.category("fields").add("l10n_bg_uic_with_fetch", L10nBgUicField);
