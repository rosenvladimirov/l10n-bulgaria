
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
            console.log("[FiscalPayment] 🚀 Fiscal printer configured, checking order type...");

            // ════════════════════════════════════════════════════════════
            // ПРОВЕРКА: Дали е СТОРНО поръчка?
            // ════════════════════════════════════════════════════════════
            const refundInfo = this._getRefundInfo(order);

            console.log("[FiscalPayment] Is refund order:", refundInfo.isRefund);

            try {
                // Създаваме fiscal printer instance
                const fiscalPrinter = new ErpNetFPPrinter(this.env, {
                    baseUrl: fiscalPrinterHost,
                    printerId: fiscalPrinterId,
                });

                let result;

                // ════════════════════════════════════════════════════════════
                // АКО Е СТОРНО - ИЗПРАЩАМЕ REVERSAL RECEIPT
                // ════════════════════════════════════════════════════════════
                if (refundInfo.isRefund && refundInfo.originalOrder) {
                    console.log("[FiscalPayment] 🔄 Processing REFUND order...");
                    console.log("[FiscalPayment] Original order:", refundInfo.originalOrder.name);

                    const reason = this._getRefundReason(order);
                    console.log("[FiscalPayment] Refund reason:", reason);

                    result = await fiscalPrinter.printReversalReceipt(
                        refundInfo.originalOrder,
                        order,
                        reason
                    );

                }
                // ════════════════════════════════════════════════════════════
                // АКО Е НОРМАЛНА ПОРЪЧКА - ИЗПРАЩАМЕ НОРМАЛЕН RECEIPT
                // ════════════════════════════════════════════════════════════
                else {
                    console.log("[FiscalPayment] 📄 Processing NORMAL order...");
                    result = await fiscalPrinter.printReceipt(order);
                }

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

                    if (refundInfo.isRefund) {
                        order.l10n_bg_is_reversal = true;  // ← Маркираме като сторно
                    }

                    window.__fiscalPrinterCurrentOrder.l10n_bg_is_fiscalized = true;
                    window.__fiscalPrinterCurrentOrder.l10n_bg_fiscal_receipt_number = result.fiscalData?.receiptNumber;
                    window.__fiscalPrinterCurrentOrder.l10n_bg_fiscal_memory_number = result.fiscalData?.fiscalMemorySerialNumber;

                    // Notification за успех
                    if (this.env?.services?.notification) {
                        const message = refundInfo.isRefund
                            ? _t("Сторно бон отпечатан ")
                            : _t("Фискален бон отпечатан ");

                        this.env.services.notification.add(
                            message +
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
                        const errorType = refundInfo.isRefund ? _t("сторно бон") : _t("фискален бон");

                        this.env.services.notification.add(
                            _t("Грешка при печат на ") + errorType + ": " +
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
    },

    /**
     * Извлича информация за сторно поръчка
     *
     * @param {Object} order - POS Order
     * @returns {Object} { isRefund: boolean, originalOrder: Object|null }
     */
    _getRefundInfo(order) {
        const orderLines = order.lines || order.get_orderlines?.() || [];

        // Проверяваме дали има линии с отрицателни количества
        // и извличаме оригиналния order
        for (const line of orderLines) {
            const qty = line.get_quantity?.() || line.qty || 0;

            // Ако има отрицателно количество И има refunded_orderline_id -> СТОРНО
            if (qty < 0 && line.refunded_orderline_id) {
                const originalOrder = line.refunded_orderline_id.order_id;

                console.log("[FiscalPayment] 📋 Found refund line:");
                console.log("[FiscalPayment]    Current line qty:", qty);
                console.log("[FiscalPayment]    Refunded line:", line.refunded_orderline_id);
                console.log("[FiscalPayment]    Original order:", originalOrder?.name);
                console.log("[FiscalPayment]    Original order fiscal #:", originalOrder?.l10n_bg_fiscal_receipt_number);

                return {
                    isRefund: true,
                    originalOrder: originalOrder,
                };
            }
        }

        return {
            isRefund: false,
            originalOrder: null,
        };
    },

    /**
     * Определя причината за сторниране
     *
     * @param {Object} order - POS Order
     * @returns {String} "operator-error", "refund", или "tax-base-reduction"
     */
    _getRefundReason(order) {
        // Може да добавите логика за избор на причина
        // Например от popup или от order properties

        // По подразбиране връщаме "refund"
        return "refund";

        // Алтернативно можете да проверите:
        // if (order.refund_reason) return order.refund_reason;
        // if (order.is_operator_error) return "operator-error";
        // if (order.is_tax_reduction) return "tax-base-reduction";
    }
});

console.log("[FiscalPayment] ✅ PaymentScreen patched successfully");
