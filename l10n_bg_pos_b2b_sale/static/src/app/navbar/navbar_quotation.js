import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

/**
 * Номерът на офертата (SO) на текущата поръчка — горе, до „Orders“ и
 * номера на поръчката в касата; натискането отваря печата ѝ
 * (ADR specs/pos-b2b-wholesale/0003).
 */
patch(Navbar.prototype, {
    get l10nBgQuotation() {
        const form = this.pos.getOrder()?.l10nBgForm;
        return form?.sale_order_id
            ? { name: form.sale_order_name, state: form.sale_order_state_label, reports: form.sale_order_reports }
            : null;
    },

    l10nBgOpenQuotation() {
        const quotation = this.l10nBgQuotation;
        if (quotation?.reports?.quotation) {
            this.pos.l10nBgReport = {
                url: quotation.reports.quotation,
                title: `${_t("Quotation")} ${quotation.name}`,
            };
        }
    },
});
