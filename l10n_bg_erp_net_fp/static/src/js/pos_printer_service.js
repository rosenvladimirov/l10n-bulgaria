/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PrinterService } from "@point_of_sale/app/printer/printer_service";

console.log("[FiscalPrinter] 🔧 Loading Fiscal Printer PrinterService Patch...");

/**
 * Patch на PrinterService.print() за да skip-нем печата
 * ако order-ът е вече фискализиран
 */
patch(PrinterService.prototype, {
    /**
     * @override
     * Проверяваме дали order-ът е вече фискализиран ПРЕДИ да печатаме
     */
    async print(component, props, options) {
        console.log("[FiscalPrinter] 🖨️ PrinterService.print() called");

        // ════════════════════════════════════════════════════════════
        // ПРОВЕРКА: Дали order-ът вече е фискализиран?
        // ════════════════════════════════════════════════════════════
        let order = null;

        // Опит да вземем order от различни източници
        if (window.__fiscalPrinterCurrentOrder) {
            order = window.__fiscalPrinterCurrentOrder;
            console.log("[FiscalPrinter]    Order from window.__fiscalPrinterCurrentOrder");
        } else if (window.__fiscalPrinterPosStore) {
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
            return true;
        }

        // ════════════════════════════════════════════════════════════
        // АКО ORDER НЕ Е ФИСКАЛИЗИРАН - НОРМАЛЕН ПЕЧАТ
        // ════════════════════════════════════════════════════════════
        console.log("[FiscalPrinter] 🟢 Order not fiscalized, proceeding with normal print");

        // Извикваме оригиналния метод
        return await super.print(component, props, options);
    },
});

console.log("[FiscalPrinter] ✅ PrinterService patched successfully");
