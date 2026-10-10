/**
 * Турове на продажбата на едро (котвата specs/pos-b2b-wholesale §23).
 * Проверките в базата са в tests/test_b2b_tour.py.
 */
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import { registry } from "@web/core/registry";

// Купувачите — същите имена като в test_b2b_tour.py
const SOLE_TRADER = "ET Petrov Trade";
const FOREIGN_BUYER = "Deutsche Kunde GmbH";

function clickWholesale() {
    return {
        content: "switch to Wholesale",
        trigger: ".control-buttons .o_l10n_bg_wholesale_button",
        run: "click",
    };
}

// Формата като в продажбата (ADR specs/pos-b2b-wholesale/0002), акордеонът
// и бутонът за обща отстъпка до „Wholesale“.
function applyFormDiscount(percent) {
    return [
        {
            content: "a new customer opens the order details (accordion)",
            trigger: ".o_l10n_bg_b2b_form .o_l10n_bg_b2b_warehouse",
        },
        {
            content: "the order lines are hidden meanwhile, the details take the whole height",
            trigger: ".o_l10n_bg_b2b_tabs[data-pane=header]",
        },
        openLines(),
        {
            content: "the order details are hidden",
            trigger: "body:not(:has(.o_l10n_bg_b2b_form))",
        },
        {
            content: "the discount button is next to Wholesale",
            trigger: ".control-buttons .o_l10n_bg_b2b_discount_button",
            run: "click",
        },
        ...String(percent).split("").map((key) => ({
            content: `discount key ${key}`,
            trigger: `.o_dialog div.numpad button:contains(/^${key}$/)`,
            run: "click",
        })),
        Dialog.confirm(),
        {
            content: "the line carries the discount",
            trigger: `.orderline .price-per-unit:contains("${percent}%")`,
        },
        {
            content: "untaxed subtotal is shown, like the sale order",
            trigger: ".order-summary .subtotal",
        },
    ];
}

function openLines() {
    return {
        content: "open the order lines",
        trigger: ".o_l10n_bg_b2b_tab_lines",
        run: "click",
    };
}

function headerShows(text) {
    return {
        content: `wholesale block shows ${text}`,
        trigger: `.o_l10n_bg_b2b_header:contains("${text}")`,
    };
}

function headerHidden() {
    return {
        content: "wholesale block is hidden",
        trigger: "body:not(:has(.o_l10n_bg_b2b_header))",
    };
}

// TOUR-W1: „Wholesale“ → ЕТ (не е is_company) → „Invoice“ отметнато и
// заключено → брой → една фактура (проверява се в Python).
registry.category("web_tour.tours").add("l10n_bg_pos_b2b_wholesale_invoice", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            clickWholesale(),
            headerShows("Choose the customer"),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer(SOLE_TRADER),
            headerShows(SOLE_TRADER),
            ...applyFormDiscount(10),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.isInvoiceButtonChecked(),
            // заключено: опитът да се размаркира не сменя нищо
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.isInvoiceButtonChecked(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

// TOUR-W5: „Retail“ (без „Wholesale“) + ЕТ → „Invoice“ се отмята от нашия
// setPartner (ядрото го прави само при is_company) и е заключено.
registry.category("web_tour.tours").add("l10n_bg_pos_b2b_retail_b2b_buyer_invoiced", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer(SOLE_TRADER),
            headerHidden(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.isInvoiceButtonChecked(),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.isInvoiceButtonChecked(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

// TOUR-W9: чуждестранен купувач → стоп „back office“ преди плащането.
registry.category("web_tour.tours").add("l10n_bg_pos_b2b_foreign_buyer_blocked", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            clickWholesale(),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer(FOREIGN_BUYER),
            headerShows("back office"),
            openLines(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            Dialog.is({ title: "Back office invoice" }),
            Dialog.confirm(),
            PaymentScreen.isShown(),
        ].flat(),
});
