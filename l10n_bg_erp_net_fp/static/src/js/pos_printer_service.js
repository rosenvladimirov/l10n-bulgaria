/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PrinterService } from "@point_of_sale/app/services/printer_service";

console.log("[FiscalPrinter] 🔧 Loading Fiscal Printer PrinterService Patch...");

/**
 * Patch на PrinterService.print() за да skip-нем печата
 * ако order-ът е вече фискализиран
 */
patch(PrinterService.prototype, {
    /**
     * @override
     * За BG фискален обект КАСОВАТА БЕЛЕЖКА от ФУ-то (dp150) Е официалната
     * бележка. Пропускаме всеки нормален/browser/IoT печат когато POS-ът има
     * конфигуриран фискален принтер — иначе `printer.print()` пада на
     * `window.print()` (защото `printOptions.webPrintFallback = true`) и
     * отваря browser print диалог.
     */
    async print(component, props, options) {
        console.log("[FiscalPrinter] 🖨️ PrinterService.print() called");

        // Order — от props (най-надеждно, директно от printReceipt call), с
        // fallback на window-globals (set от payment_screen.js).
        const order =
            props?.order
            || window.__fiscalPrinterCurrentOrder
            || (() => {
                try { return window.__fiscalPrinterPosStore?.get_order?.(); }
                catch (e) { return null; }
            })();

        // Fiscal printer config — пробваме всичко що сме видели да го носи:
        // 1) order.config_id (v19 order носи pos.config) — най-надеждно
        // 2) order.session_id.config_id
        // 3) window.__fiscalPrinterPosStore.session / .config
        // 4) order.pos (по-старо)
        const cfgSources = [
            order?.config_id,
            order?.session_id?.config_id,
            order?.session_id,
            window.__fiscalPrinterPosStore?.session,
            window.__fiscalPrinterPosStore?.config,
            order?.pos?.session,
            order?.pos?.config,
        ];
        let host = "";
        let printerId = "";
        for (const src of cfgSources) {
            if (!src) continue;
            host = host || src.l10n_bg_erp_net_fp_host || "";
            printerId = printerId || src.l10n_bg_erp_net_fp_ip || "";
            if (host && printerId) break;
        }
        const fiscalConfigured = !!(host && printerId);

        console.log("[FiscalPrinter]    Order:", order?.name);
        console.log("[FiscalPrinter]    Is fiscalized:", order?.l10n_bg_is_fiscalized);
        console.log("[FiscalPrinter]    Fiscal host:", host, "| printer:", printerId);
        console.log("[FiscalPrinter]    Fiscal configured:", fiscalConfigured);

        if (order?.l10n_bg_is_fiscalized || fiscalConfigured) {
            console.log("[FiscalPrinter] 🚫 SKIPPING normal print — фискалният бон (ФУ) е официалната бележка");
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
