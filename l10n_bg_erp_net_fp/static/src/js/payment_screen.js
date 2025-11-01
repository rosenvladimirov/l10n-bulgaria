/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ErpNetFPPrinter } from "@l10n_bg_erp_net_fp/js/erp_net_fp_printer";

console.log("[FiscalPayment] 🔧 Loading Fiscal Payment Extension...");

/**
 * Patch на PaymentScreen за да hook-нем validateOrder()
 * ПРАВИЛНОТО МЯСТО ЗА FISCAL PRINTER INTEGRATION!
 */
patch(PaymentScreen.prototype, {

    /**
     * Hook точно преди order validation
     *
     * @override
     */
    async validateOrder(isForceValidate) {
        console.log("[FiscalPayment] ═══════════════════════════════════════");
        console.log("[FiscalPayment] 🎯 validateOrder() called");
        console.log("[FiscalPayment] ═══════════════════════════════════════");

        const order = this.currentOrder;

        console.log("[FiscalPayment] Current order:", order);
        console.log("[FiscalPayment] Order name:", order?.name);
        console.log("[FiscalPayment] Order lines:", order?.lines?.length);

        // ════════════════════════════════════════════════════════════
        // ВАЖНО: Запазваме reference към order за да го използваме в BasePrinter
        // ════════════════════════════════════════════════════════════
        window.__fiscalPrinterCurrentOrder = order;
        window.__fiscalPrinterPosStore = this.pos;

        // Проверяваме дали има fiscal printer конфигуриран
        const fiscalPrinterHost = this.pos.session?.l10n_bg_erp_net_fp_host;
        const fiscalPrinterId = this.pos.session?.l10n_bg_erp_net_fp_ip;

        console.log("[FiscalPayment] Fiscal printer host:", fiscalPrinterHost);
        console.log("[FiscalPayment] Fiscal printer ID:", fiscalPrinterId);

        if (fiscalPrinterHost && fiscalPrinterId && order) {
            console.log("[FiscalPayment] 🚀 Fiscal printer configured, sending to printer...");

            try {
                // Създаваме fiscal printer instance
                const fiscalPrinter = new ErpNetFPPrinter(this.env, {
                    baseUrl: fiscalPrinterHost,
                    printerId: fiscalPrinterId,
                });

                // ════════════════════════════════════════════════════════════
                // ИЗПРАЩАМЕ КЪМ FISCAL PRINTER ПРЕДИ ДА ФИНАЛИЗИРАМЕ ORDER-А
                // ════════════════════════════════════════════════════════════
                const result = await fiscalPrinter.printReceipt(order);

                console.log("[FiscalPayment] Fiscal printer result:", result);

                if (result.successful) {
                    console.log("[FiscalPayment] ✅ Fiscal print SUCCESS!");
                    console.log("[FiscalPayment] Receipt #:", result.fiscalData?.receiptNumber);
                    console.log("[FiscalPayment] Fiscal Memory #:", result.fiscalData?.fiscalMemorySerialNumber);

                    // ════════════════════════════════════════════════════════════
                    // ЗАПИСВАМЕ FISCAL DATA В ORDER-А
                    // По този начин BasePrinter ще знае че order е фискализиран
                    // ════════════════════════════════════════════════════════════
                    order.l10n_bg_fiscal_receipt_number = result.fiscalData?.receiptNumber;
                    order.l10n_bg_fiscal_memory_number = result.fiscalData?.fiscalMemorySerialNumber;
                    order.l10n_bg_is_fiscalized = true;  // ← FLAG за BasePrinter!

                    // Notification за успех
                    if (this.env?.services?.notification) {
                        this.env.services.notification.add(
                            _t("Фискален бон отпечатан ") +
                            (result.fiscalData?.receiptNumber ? `№${result.fiscalData.receiptNumber}` : ""),
                            { type: "success" }
                        );
                    }

                } else {
                    console.error("[FiscalPayment] ❌ Fiscal print FAILED:", result);

                    // ════════════════════════════════════════════════════════════
                    // ВАЖНО: Ако fiscal печат не работи, БЛОКИРАМЕ VALIDATION-А!
                    // Това е законово изискване в България
                    // ════════════════════════════════════════════════════════════

                    if (this.env?.services?.notification) {
                        this.env.services.notification.add(
                            _t("Грешка при фискален печат: ") +
                            (result.message?.body || "Неизвестна грешка") +
                            _t("\n\nПоръчката НЕ МОЖЕ да бъде валидирана без фискален бон!"),
                            {
                                type: "danger",
                                sticky: true
                            }
                        );
                    }

                    // НЕ извикваме super.validateOrder() ако fiscal печат не работи!
                    console.log("[FiscalPayment] ⛔ Order validation BLOCKED due to fiscal print failure");
                    return;
                }

            } catch (error) {
                console.error("[FiscalPayment] ❌ Fiscal printer error:", error);
                console.error("[FiscalPayment] ❌ Error stack:", error.stack);

                if (this.env?.services?.notification) {
                    this.env.services.notification.add(
                        _t("Грешка при комуникация с фискален принтер: ") + error.message +
                        _t("\n\nПоръчката НЕ МОЖЕ да бъде валидирана без фискален бон!"),
                        {
                            type: "danger",
                            sticky: true
                        }
                    );
                }

                // НЕ извикваме super.validateOrder() при грешка!
                console.log("[FiscalPayment] ⛔ Order validation BLOCKED due to fiscal printer error");
                return;
            }
        } else {
            console.log("[FiscalPayment] ⚠️ Fiscal printer not configured or no order");
            console.log("[FiscalPayment] Proceeding with normal validation...");
        }

        // ════════════════════════════════════════════════════════════
        // АКО ВСИЧКО Е ОК (или няма fiscal printer) - ПРОДЪЛЖАВАМЕ С НОРМАЛЕН FLOW
        // ════════════════════════════════════════════════════════════
        console.log("[FiscalPayment] ✅ Proceeding to normal order validation...");
        return await super.validateOrder(isForceValidate);
    }
});

console.log("[FiscalPayment] ✅ PaymentScreen patched successfully");
