/** @odoo-module **/

/**
 * Pinpad-aware patch on PaymentScreen.
 *
 * Strict ADD-only: this is a SEPARATE patch file from the existing
 * `payment_screen.js` (which hooks `validateOrder()` for fiscal-print
 * integration). This patch hooks `addNewPaymentLine` so when a
 * payment method marked `l10n_bg_use_pinpad` is selected, the POS
 * delegates the card charge to the local Python proxy via RPC.
 *
 * The two patches are orthogonal — both can coexist on the same
 * PaymentScreen.prototype because `patch()` composes per-method.
 */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    /**
     * @override
     * Intercept payment line creation for pinpad-marked methods.
     * On success, mark the line with the pinpad transaction id.
     * On failure, prevent the line from being added.
     */
    async addNewPaymentLine(paymentMethod) {
        // Defensive: super first when method isn't pinpad-marked.
        if (!paymentMethod || !paymentMethod.l10n_bg_use_pinpad) {
            return await super.addNewPaymentLine(...arguments);
        }

        const order = this.currentOrder;
        const remaining = order.getDue();
        if (remaining <= 0) {
            // Nothing to charge — fall through to default behaviour.
            return await super.addNewPaymentLine(...arguments);
        }

        // Find a fiscal device on this POS config (any active one).
        const deviceId = this.pos.config?.l10n_bg_fiscal_printer_id?.[0]
            || this.pos.session?.l10n_bg_erp_net_fp_device_id;
        if (!deviceId) {
            this.env.services.notification.add(
                _t("No fiscal device configured for this POS — pinpad disabled."),
                { type: "warning" },
            );
            return await super.addNewPaymentLine(...arguments);
        }

        const orderName = order.name || order.uid || "";
        let result;
        try {
            result = await this.env.services.orm.call(
                "fiscal.printer.device",
                "charge_pinpad",
                [],
                {
                    device_id: deviceId,
                    amount: remaining,
                    currency: this.pos.currency?.name || "BGN",
                    pinpad_id: paymentMethod.l10n_bg_pinpad_id || null,
                    reference: orderName,
                },
            );
        } catch (err) {
            this.env.services.notification.add(
                _t("Pinpad RPC failed: %s", err.message || err),
                { type: "danger" },
            );
            return false;
        }

        if (!result || !result.ok) {
            this.env.services.notification.add(
                _t("Pinpad charge failed: %s",
                   (result && result.message) || _t("unknown error")),
                { type: "danger" },
            );
            return false;
        }

        // Charge succeeded — proceed with normal line creation, then
        // tag the new line with the pinpad transaction id (so it lands
        // on the receipt + reaches the backend).
        const ok = await super.addNewPaymentLine(...arguments);
        const newLine = order.getSelectedPaymentline();
        if (newLine && result.transaction_id) {
            newLine.set_payment_status?.("done");
            newLine.transaction_id = result.transaction_id;
        }
        this.env.services.notification.add(
            _t("Pinpad approved · ref %s", result.transaction_id || "—"),
            { type: "success" },
        );
        return ok;
    },
});
