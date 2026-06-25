/** @odoo-module **/

/**
 * Pinpad-aware patch on PaymentScreen.
 *
 * When a payment method marked `l10n_bg_use_pinpad` is selected, the POS
 * charges the card on a physical pinpad through the LOCAL ErpNet.FP proxy.
 *
 * Топология (важно): проксито, което кара pinpad-а, върви ДО POS-а (на
 * същата машина като браузъра), НЕ на Odoo сървъра. Отдалечена Odoo не
 * може да го достигне. Затова — точно както фискалният печат — БРАУЗЪРЪТ
 * вика проксито директно (browser-proxy) през advertised host-а от
 * сесията `l10n_bg_erp_net_fp_host`. Няма server-side обиколка.
 *
 * Strict ADD-only: separate patch file from `payment_screen.js` (which
 * hooks `validateOrder()`); `patch()` composes per-method so both coexist.
 */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

// Колко чакаме клиента да пъхне картата + PIN (хостовият round-trip + EMV).
const PINPAD_TIMEOUT_MS = 90000;

patch(PaymentScreen.prototype, {
    /**
     * @override
     * Прихваща създаването на платежен ред за pinpad-маркирани методи.
     * При одобрение маркира реда с транзакционната референция; при отказ
     * или грешка не добавя ред (POS остава с дължимо).
     */
    async addNewPaymentLine(paymentMethod) {
        // Defensive: super first when method isn't pinpad-marked.
        if (!paymentMethod || !paymentMethod.l10n_bg_use_pinpad) {
            return await super.addNewPaymentLine(...arguments);
        }

        const order = this.currentOrder;
        const remaining = order.get_due();
        if (remaining <= 0) {
            // Нищо за таксуване — стандартно поведение.
            return await super.addNewPaymentLine(...arguments);
        }

        // Browser-reachable прокси host — същият, който фискалният печат ползва.
        const host = this.pos.session?.l10n_bg_erp_net_fp_host;
        if (!host) {
            this.env.services.notification.add(
                _t("No ErpNet.FP proxy host configured for this POS — pinpad disabled."),
                { type: "warning" },
            );
            return await super.addNewPaymentLine(...arguments);
        }

        const pinpadId = paymentMethod.l10n_bg_pinpad_id || "default";
        const baseUrl = String(host).replace(/\/+$/, "");
        const url = `${baseUrl}/pinpads/${encodeURIComponent(pinpadId)}/purchase`;
        const orderName = order.name || order.uid || "";

        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), PINPAD_TIMEOUT_MS);
        let result;
        try {
            const resp = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    amount: remaining,
                    currency: this.pos.currency?.name || "BGN",
                    reference: orderName,
                }),
                signal: ctrl.signal,
            });
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            result = await resp.json();
        } catch (err) {
            const msg = err.name === "AbortError"
                ? _t("Pinpad timed out — no response from the terminal.")
                : _t("Pinpad request failed: %s", err.message || err);
            this.env.services.notification.add(msg, { type: "danger" });
            return false;
        } finally {
            clearTimeout(timer);
        }

        // Проксито връща HTTP 200 дори при отказ — решаваме по `ok`, не по статуса.
        if (!result || !result.ok) {
            this.env.services.notification.add(
                _t("Pinpad declined: %s", (result && result.error) || _t("unknown error")),
                { type: "danger" },
            );
            return false;
        }

        // Одобрено — добавяме реда и го маркираме с реф (RRN / auth от хоста),
        // за да попадне на бона и да стигне бекенда.
        const ok = await super.addNewPaymentLine(...arguments);
        const txid = result.rrn || result.authId || result.hostRrn || "";
        const newLine = order.get_selected_paymentline();
        if (newLine) {
            newLine.set_payment_status?.("done");
            if (txid) {
                newLine.transaction_id = txid;
            }
        }
        this.env.services.notification.add(
            _t("Pinpad approved · ref %s", txid || "—"),
            { type: "success" },
        );
        return ok;
    },
});
