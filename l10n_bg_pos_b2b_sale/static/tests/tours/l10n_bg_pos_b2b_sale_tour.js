/**
 * Тур: поръчката на едро се запазва като оферта (SO) и офертата се
 * печата в десния екран (ADR specs/pos-b2b-wholesale/0003).
 */
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10n_bg_pos_b2b_sale_quotation", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                content: "switch to Wholesale",
                trigger: ".control-buttons .o_l10n_bg_wholesale_button",
                run: "click",
            },
            ProductScreen.addOrderline("Desk Pad", "2"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("ET Petrov Trade"),
            {
                content: "not saved yet: no quotation number at the top",
                trigger: ".o_l10n_bg_b2b_quotation:not(:has(.o_l10n_bg_navbar_quotation))",
            },
            {
                content: "save as quotation",
                trigger: ".o_l10n_bg_b2b_save_quotation:enabled",
                run: "click",
            },
            {
                content: "the sale order number is at the top, next to Orders",
                trigger: ".pos-topheader .o_l10n_bg_navbar_quotation:contains(S0)",
            },
            {
                content: "the quotation is issued: no way back to retail",
                trigger: ".control-buttons .o_l10n_bg_wholesale_button:disabled",
            },
            {
                content: "the order is still wholesale",
                trigger: "body",
                run: () => {
                    const order = window.posmodel.getOrder();
                    order.l10n_bg_wholesale || (() => { throw new Error("the order left wholesale"); })();
                    // и изричното превключване (напр. от друг изглед) не го сваля
                    const { ControlButtons } = odoo.loader.modules.get(
                        "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons"
                    );
                    ControlButtons.prototype.l10nBgToggleWholesale.call({
                        pos: window.posmodel,
                        notification: { add: () => {} },
                        props: {},
                    });
                    if (!order.l10n_bg_wholesale) {
                        throw new Error("the toggle took the order back to retail");
                    }
                },
            },
            {
                content: "print the quotation",
                trigger: ".o_l10n_bg_b2b_print_quotation:enabled",
                run: "click",
            },
            {
                content: "the quotation is shown in the right pane, not in a new window",
                trigger: ".rightpane .o_l10n_bg_report_viewer iframe[src*='pdfjs'][data-report*='sale.report_saleorder']",
            },
            {
                content: "close the print",
                trigger: ".o_l10n_bg_report_close",
                run: "click",
            },
            {
                content: "the products are back",
                trigger: ".rightpane:not(:has(.o_l10n_bg_report_viewer))",
            },
            {
                content: "the quotation number at the top opens the quotation too",
                trigger: ".pos-topheader .o_l10n_bg_navbar_quotation",
                run: "click",
            },
            {
                content: "the quotation is shown again",
                trigger: ".rightpane .o_l10n_bg_report_viewer iframe",
            },
            {
                content: "close it",
                trigger: ".o_l10n_bg_report_close",
                run: "click",
            },
        ].flat(),
});
