import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { L10nBgB2bHeader } from "./b2b_header/b2b_header";
import { L10nBgB2bTabs } from "./b2b_tabs/b2b_tabs";

patch(ProductScreen, {
    components: { ...ProductScreen.components, L10nBgB2bHeader, L10nBgB2bTabs },
});

patch(ProductScreen.prototype, {
    /** Плъзгане с пръст наляво/надясно сменя двата прозореца при едро. */
    l10nBgTouchStart(ev) {
        const touch = ev.touches?.[0];
        this._l10nBgTouch = touch ? { x: touch.clientX, y: touch.clientY } : null;
    },
    l10nBgTouchEnd(ev) {
        const start = this._l10nBgTouch;
        const touch = ev.changedTouches?.[0];
        const order = this.currentOrder;
        this._l10nBgTouch = null;
        if (!start || !touch || !order?.l10n_bg_wholesale) {
            return;
        }
        const dx = touch.clientX - start.x;
        const dy = touch.clientY - start.y;
        if (Math.abs(dx) < 60 || Math.abs(dx) < 1.5 * Math.abs(dy)) {
            return;
        }
        order.l10nBgPanel = dx < 0 ? "lines" : "header";
    },
});

patch(ControlButtons.prototype, {
    /** Бутонът се вижда при включен режим и при право (група). */
    get l10nBgShowWholesaleButton() {
        const config = this.pos.config;
        return Boolean(config.l10n_bg_b2b_mode && config.l10n_bg_b2b_mode !== "off" && config.l10n_bg_b2b_user_allowed);
    },

    /**
     * „Wholesale“ ↔ „Retail“ в същата поръчка (котвата §9). Поръчката не се
     * сменя; при B2B купувач „Invoice“ остава заключено и в „Retail“.
     */
    l10nBgToggleWholesale() {
        const order = this.pos.getOrder();
        if (!order) {
            return;
        }
        order.l10n_bg_wholesale = !order.l10n_bg_wholesale;
        if (order.l10n_bg_wholesale && order.getPartner()) {
            order.setToInvoice(true);
        }
        this.props.close?.();
    },

    /** Обща отстъпка: един процент на всички редове, както в SO. */
    l10nBgClickDiscount() {
        const order = this.pos.getOrder();
        this.props.close?.();
        if (!order) {
            return;
        }
        this.dialog.add(NumberPopup, {
            title: _t("Discount for all lines (%)"),
            getPayload: (num) => {
                order.l10nBgApplyDiscount(this.env.utils.parseValidFloat(num.toString()));
            },
        });
    },
});
