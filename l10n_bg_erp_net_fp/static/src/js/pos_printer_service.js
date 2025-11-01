/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { BasePrinter } from "@point_of_sale/app/printer/base_printer";

console.log("[FiscalPrinter] 🔧 Loading Fiscal Printer BasePrinter Patch...");

/**
 * Patch на BasePrinter.printReceipt() за да skip-нем печата
 * ако order-ът е вече фискализиран
 *
 * ВАЖНО: Patch-ваме BasePrinter, не PrinterService!
 * По този начин работи за ВСИЧКИ видове принтери (IoT, ePOS, и т.н.)
 */
patch(BasePrinter.prototype, {

    /**
     * @override
     * Проверяваме дали order-ът е вече фискализиран ПРЕДИ да печатаме
     */
    async printReceipt(receipt) {
        console.log("[FiscalPrinter] 🖨️ BasePrinter.printReceipt() called");

        // ════════════════════════════════════════════════════════════
        // ПРОВЕРКА: Дали order-ът вече е фискализиран?
        // ════════════════════════════════════════════════════════════

        // Опит да вземем order от различни източници
        let order = null;

        // Метод 1: От window.__fiscalPrinterPosStore (set в payment_screen.js)
        if (window.__fiscalPrinterCurrentOrder) {
            order = window.__fiscalPrinterCurrentOrder;
            console.log("[FiscalPrinter]    Order from window.__fiscalPrinterCurrentOrder");
        }

        // Метод 2: От global POS store
        if (!order && window.__fiscalPrinterPosStore) {
            try {
                order = window.__fiscalPrinterPosStore.get_order?.();
                console.log("[FiscalPrinter]    Order from window.__fiscalPrinterPosStore");
            } catch (e) {
                console.log("[FiscalPrinter]    Could not get order from PosStore");
            }
        }

        console.log("[FiscalPrinter]    Order:", order?.name);
        console.log("[FiscalPrinter]    Is fiscalized:", order?.l10n_bg_is_fiscalized);
        console.log("[FiscalPrinter]    Fiscal receipt #:", order?.l10n_bg_fiscal_receipt_number);

        // ════════════════════════════════════════════════════════════
        // КЛЮЧОВО: Ако order е фискализиран - SKIP физическия печат!
        // ════════════════════════════════════════════════════════════
        if (order?.l10n_bg_is_fiscalized) {
            console.log("[FiscalPrinter] ✅ Order is already fiscalized");
            console.log("[FiscalPrinter] 🚫 SKIPPING physical print (already printed on fiscal printer)");
            console.log("[FiscalPrinter]    Fiscal Receipt #:", order.l10n_bg_fiscal_receipt_number);

            // Връщаме success БЕЗ да печатаме
            return { successful: true };
        }

        // ════════════════════════════════════════════════════════════
        // АКО ORDER НЕ Е ФИСКАЛИЗИРАН - НОРМАЛЕН ПЕЧАТ
        // ════════════════════════════════════════════════════════════
        console.log("[FiscalPrinter] 🟢 Order not fiscalized, proceeding with normal print");

        // Извикваме оригиналния метод
        return await super.printReceipt(receipt);
    },
});

console.log("[FiscalPrinter] ✅ BasePrinter patched successfully");
