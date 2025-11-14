/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { parseFloat } from "@web/views/fields/parsers";
import { OpeningControlPopup } from "@point_of_sale/app/store/opening_control_popup/opening_control_popup";
import { ErpNetFPPrinter } from "@l10n_bg_erp_net_fp/js/erp_net_fp_printer";

// Запазваме оригиналния confirm на popup-а
const superConfirm = OpeningControlPopup.prototype.confirm;

console.log("[FiscalOpeningControl] 🔧 Loading Fiscal Opening Control Patch...");

patch(OpeningControlPopup.prototype, {
    async confirm(...args) {
        console.log("[FiscalOpeningControl] ════════════════════════════════");
        console.log("[FiscalOpeningControl] 🎯 confirm() called");
        console.log("[FiscalOpeningControl] Opening cash:", this.state.openingCash);
        console.log("[FiscalOpeningControl] Notes:", this.state.notes);

        const amount = parseFloat(this.state.openingCash);
        const notification = this.env.services.notification;

        if (!amount) {
            console.log("[FiscalOpeningControl] ⚠️ No opening cash amount, proceeding normally...");
            // 🔧 ВАЖНО: използваме superConfirm, а НЕ this._super
            if (typeof superConfirm === "function") {
                return await superConfirm.apply(this, args);
            }
            return;
        }

        const fiscalPrinterHost = this.pos.session?.l10n_bg_erp_net_fp_host;
        const fiscalPrinterId = this.pos.session?.l10n_bg_erp_net_fp_ip;

        console.log("[FiscalOpeningControl] Fiscal printer host:", fiscalPrinterHost);
        console.log("[FiscalOpeningControl] Fiscal printer ID:", fiscalPrinterId);

        if (fiscalPrinterHost && fiscalPrinterId) {
            console.log("[FiscalOpeningControl] 🚀 Fiscal printer configured, sending opening deposit...");

            try {
                const fiscalPrinter = new ErpNetFPPrinter(this.env, {
                    baseUrl: fiscalPrinterHost,
                    printerId: fiscalPrinterId,
                });

                const reason =
                    (this.state.notes || "").trim() ||
                    "ВКАРВАНЕ ИЛИ ИЗКАРВАНЕ НА ПАРИ - Начален кеш";

                console.log("[FiscalOpeningControl] 💰 Calling depositMoney()...");
                const result = await fiscalPrinter.depositMoney(amount, reason);

                console.log("[FiscalOpeningControl] Fiscal printer result:", result);

                if (!result.successful) {
                    console.error("[FiscalOpeningControl] ❌ Fiscal opening deposit FAILED:", result);

                    notification.add(
                        _t(
                            "Грешка при фискално вкарване на пари при откриване на касата: "
                        ) +
                            (result.message?.body || _t("Неизвестна грешка")) +
                            _t(
                                "\n\nОперацията НЕ МОЖЕ да бъде завършена без фискален принтер!"
                            ),
                        { type: "danger", sticky: true }
                    );

                    console.log(
                        "[FiscalOpeningControl] ⛔ Opening control BLOCKED due to fiscal printer failure"
                    );
                    return;
                }

                console.log(
                    "[FiscalOpeningControl] ✅ Fiscal opening deposit SUCCESS!"
                );
            } catch (error) {
                console.error("[FiscalOpeningControl] ❌ Fiscal printer error:", error);

                notification.add(
                    _t(
                        "Грешка при комуникация с фискален принтер при откриване на касата: "
                    ) +
                        error.message +
                        _t(
                            "\n\nОперацията НЕ МОЖЕ да бъде завършена без фискален принтер!"
                        ),
                    { type: "danger", sticky: true }
                );

                console.log(
                    "[FiscalOpeningControl] ⛔ Opening control BLOCKED due to fiscal printer error"
                );
                return;
            }
        } else {
            console.log(
                "[FiscalOpeningControl] ⚠️ Fiscal printer not configured, proceeding without fiscal deposit..."
            );
        }

        console.log(
            "[FiscalOpeningControl] ✅ Proceeding to original OpeningControl confirm..."
        );
        if (typeof superConfirm === "function") {
            return await superConfirm.apply(this, args);
        }
        return;
    },
});

console.log("[FiscalOpeningControl] ✅ OpeningControlPopup patched successfully");
