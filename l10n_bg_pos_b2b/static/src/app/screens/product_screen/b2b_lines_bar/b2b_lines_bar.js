import { Component, useEffect } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

/**
 * Втората секция на акордеона за едро: „Редове“. Отворени са или данните
 * на поръчката, или редовете; нов ред отваря редовете сам.
 */
export class L10nBgB2bLinesBar extends Component {
    static template = "l10n_bg_pos_b2b.B2bLinesBar";
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

    get expanded() {
        return this.order?.l10nBgPanel !== "header";
    }

    get total() {
        return this.order ? this.order.currencyDisplayPriceIncl : "";
    }

    toggle() {
        this.order.l10nBgPanel = this.expanded ? "header" : "lines";
    }
}
