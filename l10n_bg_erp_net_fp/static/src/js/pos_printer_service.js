
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
     * Инициализация на фискален принтер
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

            if (pos && pos.config) {
                console.log("[PosPrinter] ✅ POS service found!");

                await new Promise(resolve => setTimeout(resolve, 1000));

                const printers = pos.orderPrinters || pos.printers || pos.config?.printers || [];
                console.log("[PosPrinter] 📋 Available printers:", printers);
                console.log("[PosPrinter] 📊 Printers count:", printers.length);

                if (printers.length > 0) {
                    printers.forEach((p, index) => {
                        console.log(`[PosPrinter] Printer ${index + 1}:`, {
                            name: p.name,
                            type: p.printer_type,
                            proxy_ip: p.l10n_bg_proxy_ip,
                            printer_id: p.l10n_bg_printer_id
                        });
                    });
                }

                const fiscalPrinterConfig = printers.find(
                    (p) => p.printer_type === "erp_net_fp" && p.l10n_bg_proxy_ip && p.l10n_bg_printer_id
                );

                if (fiscalPrinterConfig) {
                    console.log("[PosPrinter] 🎯 Found ErpNet.FP fiscal printer config:");
                    console.log("[PosPrinter]    Name:", fiscalPrinterConfig.name);
                    console.log("[PosPrinter]    Type:", fiscalPrinterConfig.printer_type);
                    console.log("[PosPrinter]    Base URL:", fiscalPrinterConfig.l10n_bg_proxy_ip);
                    console.log("[PosPrinter]    Printer ID:", fiscalPrinterConfig.l10n_bg_printer_id);

                    try {
                        this.fiscalPrinter = new ErpNetFPPrinter();
                        this.fiscalPrinter.setup({
                            baseUrl: fiscalPrinterConfig.l10n_bg_proxy_ip,
                            printerId: fiscalPrinterConfig.l10n_bg_printer_id,
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
                } else {
                    console.warn("[PosPrinter] ⚠️ No ErpNet.FP fiscal printer configured");
                    console.log("[PosPrinter] 💡 Available printer types:", printers.map(p => p.printer_type));
                    this.fiscalPrinterInitialized = true;
                    return;
                }
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
