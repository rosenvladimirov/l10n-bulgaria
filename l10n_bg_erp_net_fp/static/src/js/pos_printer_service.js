/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PrinterService } from "@point_of_sale/app/printer/printer_service";
import { ErpNetFPPrinter } from "@l10n_bg_erp_net_fp/js/erp_net_fp_printer";

/**
 * Patch на PrinterService за добавяне на ErpNet.FP поддръжка
 */
patch(PrinterService.prototype, {
    setup(env, { renderer }) {
        super.setup(...arguments);
        this.fiscalPrinter = null;
        this.standardPrinter = this.device;
        this.fiscalPrinterInitialized = false;

        // Стартираме инициализацията асинхронно
        this._initializeFiscalPrinter();
    },

    /**
     * Инициализация на фискален принтер от session данните
     */
    async _initializeFiscalPrinter() {
        if (this.fiscalPrinterInitialized) {
            return;
        }

        console.log("[PosPrinter] 🔄 Starting fiscal printer initialization...");

        // Изчакваме POS да е достъпен
        let attempts = 0;
        const maxAttempts = 20;

        while (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 500));

            const pos = this.env?.services?.pos;

            if (pos && pos.session && pos.config) {
                console.log("[PosPrinter] ✅ POS service found!");
                console.log("[PosPrinter] 📋 Session:", pos.session);
                console.log("[PosPrinter] 📋 Config:", pos.config);

                await new Promise(resolve => setTimeout(resolve, 500));

                // Фискалният принтер е в session.l10n_bg_fiscal_printer_id
                const fiscalPrinterId = pos.session.l10n_bg_fiscal_printer_id;

                console.log("[PosPrinter] 🔍 Fiscal printer ID from session:", fiscalPrinterId);

                if (!fiscalPrinterId) {
                    console.warn("[PosPrinter] ⚠️ No fiscal printer configured in session");
                    this.fiscalPrinterInitialized = true;
                    return;
                }

                // Намираме принтера в loaded data
                let fiscalPrinterConfig = null;

                // Опит 1: Директно от ID (ако е число)
                if (typeof fiscalPrinterId === 'number') {
                    if (pos.models && pos.models['fiscal.printer.device']) {
                        fiscalPrinterConfig = pos.models['fiscal.printer.device'].get(fiscalPrinterId);
                        console.log("[PosPrinter] 📋 Found fiscal printer from models");
                    }
                }
                // Опит 2: Ако е масив [id, name]
                else if (Array.isArray(fiscalPrinterId) && fiscalPrinterId.length > 0) {
                    const printerId = fiscalPrinterId[0];
                    if (pos.models && pos.models['fiscal.printer.device']) {
                        fiscalPrinterConfig = pos.models['fiscal.printer.device'].get(printerId);
                        console.log("[PosPrinter] 📋 Found fiscal printer from models (array format)");
                    }
                }

                if (!fiscalPrinterConfig) {
                    console.error("[PosPrinter] ❌ Fiscal printer not found in loaded data");
                    console.log("[PosPrinter] 💡 Available models:", Object.keys(pos.models || {}));
                    this.fiscalPrinterInitialized = true;
                    return;
                }

                console.log("[PosPrinter] 🎯 Found ErpNet.FP fiscal printer:");
                console.log("[PosPrinter]    ID:", fiscalPrinterConfig.id);
                console.log("[PosPrinter]    Name:", fiscalPrinterConfig.name);
                console.log("[PosPrinter]    Host:", fiscalPrinterConfig.host);
                console.log("[PosPrinter]    Printer ID:", fiscalPrinterConfig.printer_id);
                console.log("[PosPrinter]    Full config:", fiscalPrinterConfig);

                // Проверка дали има нужните полета
                if (!fiscalPrinterConfig.host || !fiscalPrinterConfig.printer_id) {
                    console.error("[PosPrinter] ❌ Fiscal printer config is incomplete");
                    console.log("[PosPrinter]    host:", fiscalPrinterConfig.host);
                    console.log("[PosPrinter]    printer_id:", fiscalPrinterConfig.printer_id);
                    this.fiscalPrinterInitialized = true;
                    return;
                }

                try {
                    this.fiscalPrinter = new ErpNetFPPrinter();
                    this.fiscalPrinter.setup({
                        baseUrl: fiscalPrinterConfig.host,
                        printerId: fiscalPrinterConfig.printer_id,
                        pos: pos,
                    });

                    console.log("[PosPrinter] ✅ ErpNet.FP fiscal printer initialized successfully!");

                    if (this.env?.services?.notification) {
                        this.env.services.notification.add(
                            _t("Fiscal printer ErpNet.FP is ready"),
                            { type: "success" }
                        );
                    }
                } catch (error) {
                    console.error("[PosPrinter] ❌ Error creating fiscal printer:", error);
                }

                this.fiscalPrinterInitialized = true;
                return;
            }

            console.log(`[PosPrinter] ⏳ Waiting for POS... (attempt ${attempts + 1}/${maxAttempts})`);
            attempts++;
        }

        console.error("[PosPrinter] ❌ POS service not found after maximum attempts");
        this.fiscalPrinterInitialized = true;
    },

    /**
     * @override
     * Разширяваме printHtml за да използваме фискален принтер
     */
    async printHtml(el, options = {}) {
        console.log("[PosPrinter] 🖨️ printHtml called");
        console.log("[PosPrinter]    Element:", el);
        console.log("[PosPrinter]    Options:", options);
        console.log("[PosPrinter]    Fiscal printer available:", !!this.fiscalPrinter);
        console.log("[PosPrinter]    Standard printer available:", !!this.standardPrinter);

        // Проверка дали трябва да използваме фискален принтер
        const shouldUseFiscal = this.fiscalPrinter && !options.kitchen;

        console.log("[PosPrinter]    Should use fiscal:", shouldUseFiscal);

        // Ако имаме и трябва да използваме фискален принтер
        if (shouldUseFiscal) {
            console.log("[PosPrinter] 🔵 Starting FISCAL print...");

            const originalDevice = this.device;
            this.device = this.fiscalPrinter;

            try {
                const result = await this.fiscalPrinter.printReceipt(el);

                console.log("[PosPrinter] Fiscal print result:", result);

                if (!result.successful) {
                    console.error("[PosPrinter] ❌ Fiscal print failed:", result);

                    if (this.env?.services?.notification) {
                        this.env.services.notification.add(
                            _t("Fiscal printer error: ") + (result.message?.body || "Unknown error"),
                            { type: "danger" }
                        );
                    }

                    this.device = originalDevice;

                    console.log("[PosPrinter] 🔄 Trying standard printer as fallback...");
                    return await super.printHtml(el, { ...options, webPrintFallback: true });
                }

                console.log("[PosPrinter] ✅ Fiscal print SUCCESS!");

                if (this.env?.services?.notification) {
                    this.env.services.notification.add(
                        _t("Fiscal receipt printed") +
                        (result.fiscalData?.receiptNumber ? ` №${result.fiscalData.receiptNumber}` : ""),
                        { type: "success" }
                    );
                }

                this.device = originalDevice;
                return true;

            } catch (error) {
                console.error("[PosPrinter] ❌ Fiscal print error:", error);

                this.device = originalDevice;

                console.log("[PosPrinter] 🔄 Fallback to standard printer...");
                return await super.printHtml(el, { ...options, webPrintFallback: true });
            }
        }

        // Стандартен печат
        console.log("[PosPrinter] 🟢 Using standard print");
        return await super.printHtml(el, options);
    },
});
