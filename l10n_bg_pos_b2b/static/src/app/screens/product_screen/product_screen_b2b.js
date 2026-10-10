import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { L10nBgB2bHeader } from "./b2b_header/b2b_header";

patch(ProductScreen, {
    components: { ...ProductScreen.components, L10nBgB2bHeader },
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
});
