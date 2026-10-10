import { Component, useEffect } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

/**
 * Двата прозореца на лявата колона при едро: „Данни на поръчката“ и
 * „Редове“, всеки на цялата височина. Сменят се с табовете или с плъзгане
 * наляво/надясно; нов ред отваря редовете, нов клиент — данните.
 */
export class L10nBgB2bTabs extends Component {
    static template = "l10n_bg_pos_b2b.B2bTabs";
    static props = {};

    setup() {
        this.pos = usePos();
        let previous = this.order?.lines.length || 0;
        useEffect(
            (count) => {
                if (count > previous && this.order) {
                    this.order.l10nBgPanel = "lines";
                }
                previous = count;
            },
            () => [this.order?.lines.length || 0]
        );
    }

    get order() {
        return this.pos.getOrder();
    }

    get panel() {
        return this.order?.l10nBgPanel || "header";
    }

    get partnerName() {
        return this.order?.getPartner()?.name || "";
    }

    get total() {
        return this.order ? this.order.currencyDisplayPriceIncl : "";
    }

    show(panel) {
        this.order.l10nBgPanel = panel;
    }
}
