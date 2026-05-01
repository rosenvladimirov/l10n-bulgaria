/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { parseFloat } from "@web/views/fields/parsers";
import { OpeningControlPopup } from "@point_of_sale/app/store/opening_control_popup/opening_control_popup";
import { DatecsPMPrinter } from "@l10n_bg_fiscal_printer_datecs_pm/js/datecs_pm_printer";

const superConfirm = OpeningControlPopup.prototype.confirm;

/**
 * Patch OpeningControlPopup.confirm() — register the opening cash
 * float as a cash-in on the Datecs PM device, so the device's safe
 * total starts the day in sync with Odoo.
 *
 * Sibling reference:
 *   l10n_bg_erp_net_fp/static/src/js/opening_control_popup_fiscal.js
 */
patch(OpeningControlPopup.prototype, {
    async confirm(...args) {
        const amount = parseFloat(this.state.openingCash);
        if (!amount) {
            return typeof superConfirm === "function"
                ? await superConfirm.apply(this, args)
                : undefined;
        }

        const session = this.pos.session;
        const proxyUrl = session?.l10n_bg_fp_datecs_proxy_url;
        const printerId = session?.l10n_bg_fp_datecs_printer_id;
        if (!proxyUrl || !printerId) {
            return typeof superConfirm === "function"
                ? await superConfirm.apply(this, args)
                : undefined;
        }

        const printer = new DatecsPMPrinter(this.env, {
            proxyUrl,
            printerId,
            posConfigId: this.pos.config?.id,
            sessionId: session.id,
        });

        const reason =
            (this.state.notes || "").trim() ||
            _t("Opening cash float");

        const notification = this.env.services.notification;
        try {
            const result = await printer.cashIn(amount, reason);
            if (!result || !result.ok) {
                if (notification) {
                    notification.add(
                        _t("Datecs PM opening deposit error: ") +
                            (result?.error || _t("Unknown error")) +
                            _t(
                                "\n\nPOS opening cannot complete without device confirmation.",
                            ),
                        { type: "danger", sticky: true },
                    );
                }
                return;  // BLOCK opening
            }
        } catch (error) {
            if (notification) {
                notification.add(
                    _t("Datecs PM communication error: ") +
                        error.message +
                        _t(
                            "\n\nPOS opening cannot complete without device confirmation.",
                        ),
                    { type: "danger", sticky: true },
                );
            }
            return;
        }

        return typeof superConfirm === "function"
            ? await superConfirm.apply(this, args)
            : undefined;
    },
});
