/**
 * Проверките на продажбата на едро — ПРЕДИ плащането (котвата §10).
 *
 * Чисти функции върху поръчката и касата: OrderPaymentValidation ги вика,
 * B2B блокът над продуктите показва същите числа. Сървърът не вдига грешки
 * при синхронизация — затова всичко, което трябва да спре продажбата,
 * е тук.
 */
import { _t } from "@web/core/l10n/translation";

/** Етикетите на липсите по ЗДДС чл. 114 (кодовете идват от сървъра). */
export function l10nBgMissingLabels(partner) {
    const labels = {
        name: _t("name"),
        address: _t("address (street, city, country)"),
        uic: _t("company ID (UIC) or VAT number"),
    };
    const codes = (partner?.l10n_bg_invoice_missing || "").split(",").filter(Boolean);
    return codes.map((code) => labels[code] || code);
}

/** Сумата „на сметка“ (pay_later) в поръчката. */
export function l10nBgOnAccountAmount(order) {
    return (order.payment_ids || [])
        .filter((p) => p.payment_method_id?.type === "pay_later")
        .reduce((sum, p) => sum + (p.getAmount ? p.getAmount() : p.amount || 0), 0);
}

/**
 * Кредитът на купувача към момента на зареждане (котвата §15.2):
 * използван = отворено вземане + „на сметка“ в отворени сесии (сървър)
 * + „на сметка“ в платените, още несинхронизирани поръчки на тази каса.
 */
export function l10nBgCreditState(pos, order) {
    const partner = order.getPartner();
    if (!partner) {
        return null;
    }
    const unsynced = pos.data?.localUnsyncedPaidOrderUuids || new Set();
    const localDue = pos.models["pos.order"]
        .filter(
            (o) =>
                o.uuid !== order.uuid &&
                unsynced.has(o.uuid) &&
                o.getPartner()?.id === partner.id
        )
        .reduce((sum, o) => sum + l10nBgOnAccountAmount(o), 0);
    const limit = partner.l10n_bg_pos_credit_limit || 0;
    const used =
        (partner.l10n_bg_pos_total_due || 0) +
        (partner.l10n_bg_pos_orders_amount_due || 0) +
        localDue;
    const onAccount = l10nBgOnAccountAmount(order);
    return {
        limit,
        used,
        overdue: partner.l10n_bg_pos_overdue || 0,
        onAccount,
        exceeded: limit > 0 && onAccount > 0 && used + onAccount > limit,
    };
}

/** Фактура е задължителна: B2B купувач или режим „Wholesale“ с клиент. */
export function l10nBgInvoiceRequired(order) {
    const partner = order.getPartner();
    return Boolean(partner && (partner.l10n_bg_is_b2b_buyer || order.l10n_bg_wholesale));
}

/**
 * Твърдите спирания. Всеки елемент: {title, body}.
 * Празен списък = може да се плаща.
 */
export function l10nBgB2bBlockers(pos, order) {
    const config = pos.config;
    const partner = order.getPartner();
    const blockers = [];
    if (order.l10n_bg_wholesale && !partner) {
        blockers.push({
            title: _t("Customer required"),
            body: _t("Select the business customer before payment in Wholesale mode."),
        });
        return blockers;
    }
    if (!partner) {
        return blockers;
    }
    if (l10nBgInvoiceRequired(order) && !order.isToInvoice()) {
        // Гардът „фирма без фактура“ — никой не може да го отмени (§21).
        blockers.push({
            title: _t("Invoice required"),
            body: _t(
                "%s is a business customer and must receive an invoice. Mark the order for invoicing.",
                partner.name
            ),
        });
    }
    if (!order.l10nBgIsB2b) {
        return blockers;
    }
    if (partner.l10n_bg_b2b_route === "backoffice") {
        blockers.push({
            title: _t("Back office invoice"),
            body: _t(
                "This customer must be invoiced from the back office (intra-EU / export)."
            ),
        });
    }
    const currency = order.pricelist_id?.currency_id;
    if (currency && pos.currency && currency.id !== pos.currency.id) {
        blockers.push({
            title: _t("Foreign currency"),
            body: _t(
                "The pricelist %(pricelist)s is in %(currency)s. Wholesale sales in the Point of Sale are only possible in %(company_currency)s.",
                {
                    pricelist: order.pricelist_id.display_name || order.pricelist_id.name,
                    currency: currency.name,
                    company_currency: pos.currency.name,
                }
            ),
        });
    }
    const missing = l10nBgMissingLabels(partner);
    if (missing.length && config.l10n_bg_b2b_guard_mode === "block") {
        blockers.push({
            title: _t("Incomplete invoice details"),
            body: _t("The invoice details of %(partner)s are incomplete: %(missing)s.", {
                partner: partner.name,
                missing: missing.join(", "),
            }),
        });
    }
    const credit = l10nBgCreditState(pos, order);
    if (credit?.exceeded && config.l10n_bg_b2b_credit_policy === "block") {
        blockers.push({
            title: _t("Credit limit exceeded"),
            body: _t(
                "The credit limit of %(partner)s is %(limit)s; already used %(used)s. This order adds %(amount)s on account.",
                {
                    partner: partner.name,
                    limit: pos.env.utils.formatCurrency(credit.limit),
                    used: pos.env.utils.formatCurrency(credit.used),
                    amount: pos.env.utils.formatCurrency(credit.onAccount),
                }
            ),
        });
    }
    const cap = config.l10n_bg_b2b_offline_order_cap || 0;
    if (credit && pos.data?.network?.offline && cap > 0 && credit.onAccount > cap) {
        blockers.push({
            title: _t("Offline credit cap"),
            body: _t(
                "The Point of Sale is offline: at most %s can be sold on account in one order.",
                pos.env.utils.formatCurrency(cap)
            ),
        });
    }
    return blockers;
}

/**
 * Предупрежденията, които касиерът потвърждава (режим `warn`).
 * Всеки елемент: {kind: "data"|"credit", text}.
 */
export function l10nBgB2bWarnings(pos, order) {
    const config = pos.config;
    const partner = order.getPartner();
    const warnings = [];
    if (!partner || !order.l10nBgIsB2b) {
        return warnings;
    }
    const missing = l10nBgMissingLabels(partner);
    if (missing.length && config.l10n_bg_b2b_guard_mode !== "block") {
        warnings.push({
            kind: "data",
            text: _t("Incomplete invoice details: %s.", missing.join(", ")),
        });
    }
    const credit = l10nBgCreditState(pos, order);
    if (credit?.exceeded && config.l10n_bg_b2b_credit_policy !== "block") {
        warnings.push({
            kind: "credit",
            text: _t("Credit limit %(limit)s exceeded: used %(used)s, this order %(amount)s.", {
                limit: pos.env.utils.formatCurrency(credit.limit),
                used: pos.env.utils.formatCurrency(credit.used),
                amount: pos.env.utils.formatCurrency(credit.onAccount),
            }),
        });
    }
    return warnings;
}
