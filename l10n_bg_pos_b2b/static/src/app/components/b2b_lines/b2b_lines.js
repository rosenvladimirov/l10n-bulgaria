import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

/**
 * Ред на поръчка на едро: единичната цена без ДДС се вижда винаги, както
 * в продажбата (SO), не само при количество различно от 1
 * (ADR specs/pos-b2b-wholesale/0002).
 */
patch(Orderline.prototype, {
    get lineScreenValues() {
        const vals = super.lineScreenValues;
        const line = this.line;
        if (
            line.order_id?.l10n_bg_wholesale &&
            this.props.mode !== "receipt" &&
            !line.combo_parent_id &&
            line.price_unit
        ) {
            // Мерната на РЕДА — при пакет (напр. pos_variant_uom) цената е за кашон.
            vals.displayPriceUnit = `${line.currencyDisplayPriceUnit} / ${
                line.getUnit?.()?.name || line.product_id?.uom_id?.name || ""
            }`;
        }
        return vals;
    },
});
