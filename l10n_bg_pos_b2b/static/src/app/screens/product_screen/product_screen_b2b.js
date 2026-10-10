import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { L10nBgB2bHeader } from "./b2b_header/b2b_header";
import { L10nBgB2bLinesBar } from "./b2b_lines_bar/b2b_lines_bar";

patch(ProductScreen, {
    components: { ...ProductScreen.components, L10nBgB2bHeader, L10nBgB2bLinesBar },
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
