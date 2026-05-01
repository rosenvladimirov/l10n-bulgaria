/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { CashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";
import { DatecsPMPrinter } from "@l10n_bg_fiscal_printer_datecs_pm/js/datecs_pm_printer";

/**
 * Patch CashMovePopup.confirm() — register cash in/out on the Datecs
 * PM device (cmd 0x46) BEFORE Odoo accepts the cash move.
 *
 * Sibling reference: l10n_bg_erp_net_fp/static/src/js/cash_move_popup.js
 */
patch(CashMovePopup.prototype, {
    async confirm() {
        const amount = parseFloat(this.state.amount);
        if (!amount) {
            return super.confirm();
        }

        const session = this.pos.session;
        const proxyUrl = session?.l10n_bg_fp_datecs_proxy_url;
        const printerId = session?.l10n_bg_fp_datecs_printer_id;
        if (!proxyUrl || !printerId) {
            return super.confirm();
        }

        const printer = new DatecsPMPrinter(this.env, {
            proxyUrl,
            printerId,
            posConfigId: this.pos.config?.id,
            sessionId: session.id,
        });

        const reason = (this.state.reason || "").trim();
        let result;
        try {
            if (this.state.type === "in") {
                result = await printer.cashIn(
                    amount,
                    reason || _t("Cash in"),
                );
            } else {
                result = await printer.cashOut(
                    amount,
                    reason || _t("Cash out"),
                );
            }
        } catch (error) {
            this._notifyCashFailure(error.message);
            return;
        }

        if (!result || !result.ok) {
            this._notifyCashFailure(
                result?.error || _t("Unknown error from device"),
            );
            return;
        }

        return super.confirm();
    },

    _notifyCashFailure(message) {
        if (!this.notification) return;
        this.notification.add(
            _t("Datecs PM cash op error: ") +
                message +
                _t(
                    "\n\nCash move cannot complete without device confirmation.",
                ),
            { type: "danger", sticky: true },
        );
    },
});
