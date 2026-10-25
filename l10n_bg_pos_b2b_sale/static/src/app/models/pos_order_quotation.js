import { serializeDate } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

/**
 * Поръчката на едро ↔ офертата (SO): заявката за запис и резултатът.
 * Ползват я формата и редакторите на редовете (ADR pos-b2b-wholesale/0003).
 */
patch(PosOrder.prototype, {
    get l10nBgShippingDateIso() {
        const date = this.shipping_date;
        if (!date) {
            return false;
        }
        return typeof date === "string" ? date.slice(0, 10) : serializeDate(date);
    },

    l10nBgQuotationPayload() {
        const form = this.l10nBgForm;
        return {
            sale_order_id: form.sale_order_id || false,
            partner_id: this.getPartner()?.id || false,
            pricelist_id: this.pricelist_id?.id || false,
            client_order_ref: this.client_order_ref || false,
            shipping_date: this.l10nBgShippingDateIso,
            pos_reference: this.pos_reference || this.name || false,
            form,
            lines: this.lines
                .filter((line) => !line.combo_parent_id)
                .map((line) => ({
                    uuid: line.uuid,
                    product_id: line.product_id.id,
                    qty: line.qty,
                    // Мерната на реда: при пакет (напр. pos_variant_uom) `qty` е в
                    // кашони, а цената — за кашон; офертата трябва да е в същата мерна.
                    product_uom_id: line.getUnit?.()?.id || false,
                    price_unit: line.price_unit,
                    discount: line.discount || 0,
                })),
        };
    },

    /**
     * Издадена оферта (SO) заключва поръчката на едро: към дребно (бон без
     * фактура) не се връща — офертата е издадена към фирмата
     * (Росен, 25.10.2026; ADR pos-b2b-wholesale/0005).
     */
    get l10nBgWholesaleLocked() {
        return Boolean(this.l10n_bg_wholesale && this.l10nBgForm.sale_order_id);
    },

    l10nBgApplyQuotation(result) {
        this.l10nBgSetForm({
            sale_order_id: result.id,
            sale_order_name: result.name,
            sale_order_state_label: result.state_label,
            sale_order_reports: result.reports,
        });
    },
});
