import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    /**
     * Ядрото отмята „Invoice“ само при `is_company`. B2B купувачът (ЕТ,
     * ДДС номер, ръчен признак) също се фактурира винаги (котвата §10.2).
     * В режим `auto_on_company` изборът на B2B купувач включва „Wholesale“.
     */
    setPartner(partner) {
        super.setPartner(...arguments);
        if (partner?.l10n_bg_is_b2b_buyer) {
            this.setToInvoice(true);
            if (this.config?.l10n_bg_b2b_mode === "auto_on_company") {
                this.l10n_bg_wholesale = true;
            }
        } else if (partner && this.l10n_bg_wholesale) {
            // Режим „Wholesale“ с клиент = продажба с фактура
            this.setToInvoice(true);
        }
    },

    /** Продажба на едро: режим „Wholesale“ или B2B купувач. */
    get l10nBgIsB2b() {
        return Boolean(this.l10n_bg_wholesale || this.getPartner()?.l10n_bg_is_b2b_buyer);
    },

    /** „Invoice“ е заключено: фактурата е задължителна. */
    get l10nBgInvoiceLocked() {
        const partner = this.getPartner();
        return Boolean(partner && (partner.l10n_bg_is_b2b_buyer || this.l10n_bg_wholesale));
    },
});
