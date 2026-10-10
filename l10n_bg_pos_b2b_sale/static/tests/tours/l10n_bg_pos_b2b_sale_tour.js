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
                content: "not saved yet",
                trigger: ".o_l10n_bg_b2b_quotation:not(:has(.o_l10n_bg_b2b_quotation_name))",
            },
            {
                content: "save as quotation",
                trigger: ".o_l10n_bg_b2b_save_quotation:enabled",
                run: "click",
            },
            {
                content: "the sale order number is shown",
                trigger: ".o_l10n_bg_b2b_quotation_name:contains(S0)",
            },
            {
                content: "print the quotation",
                trigger: ".o_l10n_bg_b2b_print_quotation:enabled",
                run: "click",
            },
            {
                content: "the quotation is shown in the right pane, not in a new window",
                trigger: ".rightpane .o_l10n_bg_report_viewer iframe[src*='sale.report_saleorder']",
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
        ].flat(),
});
