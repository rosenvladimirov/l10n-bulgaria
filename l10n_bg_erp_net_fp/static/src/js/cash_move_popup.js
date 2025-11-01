/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { CashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";
import { ErpNetFPPrinter } from "@l10n_bg_erp_net_fp/js/erp_net_fp_printer";

console.log("[FiscalCashMove] 🔧 Loading Fiscal Cash Move Patch...");

/**
 * Patch на CashMovePopup за да извикваме fiscal printer deposit/withdraw
 */
patch(CashMovePopup.prototype, {

    /**
     * @override
     * Hook преди да се изпрати cash move към сървъра
     */
    async confirm() {
        console.log("[FiscalCashMove] ═══════════════════════════════════════");
        console.log("[FiscalCashMove] 🎯 confirm() called");
        console.log("[FiscalCashMove] ═══════════════════════════════════════");
        console.log("[FiscalCashMove] Type:", this.state.type);
        console.log("[FiscalCashMove] Amount:", this.state.amount);
        console.log("[FiscalCashMove] Reason:", this.state.reason);

        const amount = parseFloat(this.state.amount);

        if (!amount) {
            const formattedAmount = this.env.utils.formatCurrency(amount);
            this.notification.add(_t("Cash in/out of %s is ignored.", formattedAmount));
            return this.props.close();
        }

        // ════════════════════════════════════════════════════════════
        // ПРОВЕРКА: Дали има конфигуриран fiscal printer?
        // ════════════════════════════════════════════════════════════
        const fiscalPrinterHost = this.pos.session?.l10n_bg_erp_net_fp_host;
        const fiscalPrinterId = this.pos.session?.l10n_bg_erp_net_fp_ip;

        console.log("[FiscalCashMove] Fiscal printer host:", fiscalPrinterHost);
        console.log("[FiscalCashMove] Fiscal printer ID:", fiscalPrinterId);

        if (fiscalPrinterHost && fiscalPrinterId) {
            console.log("[FiscalCashMove] 🚀 Fiscal printer configured, sending to fiscal printer...");

            try {
                // Създаваме fiscal printer instance
                const fiscalPrinter = new ErpNetFPPrinter(this.env, {
                    baseUrl: fiscalPrinterHost,
                    printerId: fiscalPrinterId,
                });

                const reason = this.state.reason.trim();
                let result;

                // ════════════════════════════════════════════════════════════
                // ВКАРВАНЕ ИЛИ ИЗКАРВАНЕ НА ПАРИ
                // ════════════════════════════════════════════════════════════
                if (this.state.type === "in") {
                    console.log("[FiscalCashMove] 💰 Calling depositMoney()...");
                    result = await fiscalPrinter.depositMoney(amount, reason || "Вкарване на пари");
                } else {
                    console.log("[FiscalCashMove] 💸 Calling withdrawMoney()...");
                    result = await fiscalPrinter.withdrawMoney(amount, reason || "Изкарване на пари");
                }

                console.log("[FiscalCashMove] Fiscal printer result:", result);

                if (!result.successful) {
                    console.error("[FiscalCashMove] ❌ Fiscal cash move FAILED:", result);

                    // БЛОКИРАМЕ операцията ако fiscal printer не работи
                    this.notification.add(
                        _t("Грешка при фискален ") +
                        (this.state.type === "in" ? _t("deposit") : _t("withdraw")) +
                        ": " +
                        (result.message?.body || "Неизвестна грешка") +
                        _t("\n\nОперацията НЕ МОЖЕ да бъде завършена без фискален принтер!"),
                        {
                            type: "danger",
                            sticky: true
                        }
                    );

                    // НЕ извикваме super.confirm() ако fiscal операцията не е успешна!
                    console.log("[FiscalCashMove] ⛔ Cash move BLOCKED due to fiscal printer failure");
                    return;
                }

                console.log("[FiscalCashMove] ✅ Fiscal cash move SUCCESS!");

            } catch (error) {
                console.error("[FiscalCashMove] ❌ Fiscal printer error:", error);

                this.notification.add(
                    _t("Грешка при комуникация с фискален принтер: ") + error.message +
                    _t("\n\nОперацията НЕ МОЖЕ да бъде завършена без фискален принтер!"),
                    {
                        type: "danger",
                        sticky: true
                    }
                );

                // НЕ извикваме super.confirm() при грешка!
                console.log("[FiscalCashMove] ⛔ Cash move BLOCKED due to fiscal printer error");
                return;
            }
        } else {
            console.log("[FiscalCashMove] ⚠️ Fiscal printer not configured");
            console.log("[FiscalCashMove] Proceeding with normal cash move...");
        }

        // ════════════════════════════════════════════════════════════
        // АКО ВСИЧКО Е ОК (или няма fiscal printer) - ПРОДЪЛЖАВАМЕ С НОРМАЛЕН FLOW
        // ════════════════════════════════════════════════════════════
        console.log("[FiscalCashMove] ✅ Proceeding to normal cash move...");

        // Извикваме оригиналния метод за да завърши Odoo операцията
        return await super.confirm();
    }
});

console.log("[FiscalCashMove] ✅ CashMovePopup patched successfully");
