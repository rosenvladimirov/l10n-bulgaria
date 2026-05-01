/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { DatecsPMPrinter } from "@l10n_bg_fiscal_printer_datecs_pm/js/datecs_pm_printer";

/**
 * Patch PaymentScreen.validateOrder() — fiscalize on the Datecs PM
 * device BEFORE Odoo accepts the payment as final. If the device
 * fails or is unreachable, BLOCK validation (Bulgarian fiscal law).
 *
 * Sibling reference: l10n_bg_erp_net_fp/static/src/js/payment_screen.js
 */
patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        const session = this.pos.session;
        const proxyUrl = session?.l10n_bg_fp_datecs_proxy_url;
        const printerId = session?.l10n_bg_fp_datecs_printer_id;

        if (!proxyUrl || !printerId || !order) {
            // No Datecs configured (or no order) — fall through to default flow
            return await super.validateOrder(isForceValidate);
        }

        // Skip if already fiscalized (re-entry guard)
        if (order.l10n_bg_fp_datecs_is_fiscalized) {
            return await super.validateOrder(isForceValidate);
        }

        const printer = new DatecsPMPrinter(this.env, {
            proxyUrl,
            printerId,
            posConfigId: this.pos.config?.id,
            sessionId: session.id,
        });

        let result;
        try {
            result = await printer.printReceipt(order);
        } catch (error) {
            this._notifyFiscalFailure(error.message);
            return; // BLOCK validation
        }

        if (!result.successful) {
            this._notifyFiscalFailure(
                result.message?.body || _t("Unknown error from device"),
            );
            return; // BLOCK validation per fiscal law
        }

        // Success — show notification, then proceed with default validation
        if (this.env?.services?.notification) {
            const num = result.fiscalData?.receiptNumber;
            this.env.services.notification.add(
                _t("Fiscal receipt printed") +
                    (num ? ` №${num}` : ""),
                { type: "success" },
            );
        }
        return await super.validateOrder(isForceValidate);
    },

    _notifyFiscalFailure(message) {
        if (!this.env?.services?.notification) return;
        this.env.services.notification.add(
            _t("Datecs PM error: ") +
                message +
                _t(
                    "\n\nOrder cannot be validated without a fiscal receipt.",
                ),
            { type: "danger", sticky: true },
        );
    },
});
