import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

/** Ключовете на формата за едро (ADR specs/pos-b2b-wholesale/0002). */
const L10N_BG_PARTNER_KEYS = ["invoice_partner_id", "shipping_partner_id", "payment_term_id", "salesperson_id"];

patch(PosOrder.prototype, {
    /**
     * Ядрото отмята „Invoice“ само при `is_company`. B2B купувачът (ЕТ,
     * ДДС номер, ръчен признак) също се фактурира винаги (котвата §10.2).
     * В режим `auto_on_company` изборът на B2B купувач включва „Wholesale“.
     */
    setPartner(partner) {
        const previous = this.getPartner?.();
        super.setPartner(...arguments);
        if (previous?.id !== partner?.id) {
            // Адресите и срокът са на клиента — новият клиент ги сменя.
            this.l10nBgSetForm(Object.fromEntries(L10N_BG_PARTNER_KEYS.map((k) => [k, false])));
        }
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

    /** Формата за едро (като в SO); сървърът я проверява при sync. */
    get l10nBgForm() {
        return this.l10n_bg_b2b_form || {};
    },

    l10nBgSetForm(values) {
        this.l10n_bg_b2b_form = { ...this.l10nBgForm, ...values };
    },

    /** Обща отстъпка: един процент на всички редове, както в SO. */
    l10nBgApplyDiscount(percent) {
        const value = Math.min(Math.max(Number(percent) || 0, 0), 100);
        for (const line of this.lines) {
            if (!line.combo_parent_id) {
                line.setDiscount(value);
            }
        }
    },
});
