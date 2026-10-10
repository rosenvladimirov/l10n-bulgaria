import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { l10nBgCreditState, l10nBgMissingLabels } from "../../../utils/b2b_checks";

/**
 * B2B блокът над редовете на ProductScreen (котвата §9). Тънък: само
 * показва купувача, кредита и липсите и пише полетата на поръчката.
 * Редовете, цените и данъците остават на ядрото.
 */
export class L10nBgB2bHeader extends Component {
    static template = "l10n_bg_pos_b2b.B2bHeader";
    static props = {};

    setup() {
        this.pos = usePos();
    }

    get order() {
        return this.pos.getOrder();
    }

    get partner() {
        return this.order?.getPartner();
    }

    get missing() {
        return l10nBgMissingLabels(this.partner);
    }

    get credit() {
        return this.order ? l10nBgCreditState(this.pos, this.order) : null;
    }

    get creditClass() {
        const credit = this.credit;
        if (!credit || !credit.limit) {
            return "";
        }
        if (credit.used + credit.onAccount > credit.limit) {
            return "text-danger";
        }
        return credit.used > credit.limit * 0.8 ? "text-warning" : "text-success";
    }

    get isOffline() {
        return Boolean(this.pos.data?.network?.offline);
    }

    formatCurrency(amount) {
        return this.env.utils.formatCurrency(amount || 0);
    }

    selectPartner() {
        this.pos.selectPartner();
    }

    onChangeReference(ev) {
        this.order.client_order_ref = ev.target.value || false;
    }
}
