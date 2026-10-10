import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

/**
 * Редовете на поръчка на едро — без ДДС, като в продажбата (SO)
 * (ADR specs/pos-b2b-wholesale/0002). Сменя се само показването: цените
 * и данъците се смятат от ядрото, както при `iface_tax_included='subtotal'`.
 */
patch(PosOrderline.prototype, {
    get l10nBgShowExcluded() {
        return Boolean(this.order_id?.l10n_bg_wholesale);
    },
    get displayPrice() {
        if (!this.l10nBgShowExcluded) {
            return super.displayPrice;
        }
        return this.combo_line_ids.length
            ? this.combo_line_ids.reduce((total, cl) => total + cl.priceExcl, 0)
            : this.priceExcl;
    },
    get displayPriceNoDiscount() {
        if (!this.l10nBgShowExcluded) {
            return super.displayPriceNoDiscount;
        }
        return this.combo_line_ids.length
            ? this.combo_line_ids.reduce((total, cl) => total + cl.priceExclNoDiscount, 0)
            : this.priceExclNoDiscount;
    },
    get displayPriceUnit() {
        if (!this.l10nBgShowExcluded) {
            return super.displayPriceUnit;
        }
        return this.unitPrices.total_excluded;
    },
});
