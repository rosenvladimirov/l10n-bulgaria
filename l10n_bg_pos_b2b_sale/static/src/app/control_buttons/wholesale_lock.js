import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

/**
 * След издадена оферта (SO) поръчката остава на едро — „Wholesale“ не
 * връща към дребно (Росен, 25.10.2026; ADR pos-b2b-wholesale/0005).
 */
patch(ControlButtons.prototype, {
    l10nBgToggleWholesale() {
        const order = this.pos.getOrder();
        if (order?.l10nBgWholesaleLocked) {
            this.notification.add(
                _t("Quotation %s is issued: the order stays wholesale.", order.l10nBgForm.sale_order_name || ""),
                { type: "warning" }
            );
            this.props.close?.();
            return;
        }
        return super.l10nBgToggleWholesale(...arguments);
    },
});
