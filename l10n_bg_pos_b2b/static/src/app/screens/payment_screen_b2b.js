import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    /**
     * „Invoice“ е заключено за B2B купувач и в режим „Wholesale“ —
     * гардът „фирма без фактура“ не се отменя от никого (котвата §21).
     */
    async toggleIsToInvoice() {
        const order = this.currentOrder;
        if (order?.l10nBgInvoiceLocked && order.isToInvoice()) {
            this.notification.add(_t("Business customers are always invoiced."), {
                type: "warning",
            });
            return;
        }
        return super.toggleIsToInvoice(...arguments);
    },
});
