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
        this.standardPrinter = this.device; // Запазваме оригиналния принтер
        this._initializeFiscalPrinter();
    },

    /**
     * Инициализация на фискален принтер
     */
    async _initializeFiscalPrinter() {
        console.log("[PosPrinter] Initializing fiscal printer...");

        // Изчакваме малко за да се зареди POS
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Намираме pos от env
        const pos = this.env?.services?.pos;
        if (!pos || !pos.config) {
            console.warn("[PosPrinter] POS not available yet");
            return;
        }

        const printers = pos.orderPrinters || pos.printers || pos.config?.printers || [];
        console.log("[PosPrinter] Available printers:", printers);

        const fiscalPrinterConfig = printers.find(
            (p) => p.printer_type === "erp_net_fp" && p.l10n_bg_proxy_ip && p.l10n_bg_printer_id
        );

        if (fiscalPrinterConfig) {
            console.log("[PosPrinter] Found fiscal printer config:", fiscalPrinterConfig);

            this.fiscalPrinter = new ErpNetFPPrinter();
            this.fiscalPrinter.setup({
                baseUrl: fiscalPrinterConfig.l10n_bg_proxy_ip,
                printerId: fiscalPrinterConfig.l10n_bg_printer_id,
                pos: pos,
            });

            console.log("[PosPrinter] ✅ ErpNet.FP fiscal printer initialized!");
            console.log(`[PosPrinter] Base URL: ${fiscalPrinterConfig.l10n_bg_proxy_ip}`);
            console.log(`[PosPrinter] Printer ID: ${fiscalPrinterConfig.l10n_bg_printer_id}`);

            // Показваме notification ако е наличен
            if (this.env?.services?.notification) {
                this.env.services.notification.add(
                    _t("Fiscal printer ErpNet.FP initialized"),
                    { type: "success" }
                );
            }
        } else {
            console.warn("[PosPrinter] ⚠️ No fiscal printer configured");
        }
    },

    /**
     * Избор на принтер според контекста
     */
    _selectPrinter(options = {}) {
        // Ако има фискален принтер И не е kitchen order
        if (this.fiscalPrinter && !options.kitchen) {
            console.log("[PosPrinter] ✅ Using FISCAL printer");
            return this.fiscalPrinter;
        }

        // Стандартен принтер за останалите случаи
        console.log("[PosPrinter] ✅ Using STANDARD printer");
        return this.standardPrinter;
    },

    /**
     * @override
     * Разширяваме printHtml за да използваме фискален принтер
     */
    async printHtml(el, options = {}) {
        const selectedPrinter = this._selectPrinter(options);

        // Ако е избран фискален принтер
        if (selectedPrinter === this.fiscalPrinter) {
            console.log("[PosPrinter] 🔵 Starting FISCAL print...");

            // Временно заменяме device
            const originalDevice = this.device;
            this.device = selectedPrinter;

            try {
                const result = await selectedPrinter.printReceipt(el);

                if (!result.successful) {
                    console.error("[PosPrinter] ❌ Fiscal print failed:", result);

                    // Показваме грешка
                    if (this.env?.services?.notification) {
                        this.env.services.notification.add(
                            _t("Fiscal printer error: ") + (result.message?.body || "Unknown error"),
                            { type: "danger" }
                        );
                    }

                    // Възстановяваме оригиналния device
                    this.device = originalDevice;

                    // Опитваме със стандартния принтер
                    console.log("[PosPrinter] Trying standard printer...");
                    return await super.printHtml(el, { ...options, webPrintFallback: true });
                }

                console.log("[PosPrinter] ✅ Fiscal print success!");

                // Показваме успех
                if (this.env?.services?.notification) {
                    this.env.services.notification.add(
                        _t("Fiscal receipt printed") +
                        (result.fiscalData?.receiptNumber ? ` №${result.fiscalData.receiptNumber}` : ""),
                        { type: "success" }
                    );
                }

                // Възстановяваме device
                this.device = originalDevice;
                return true;

            } catch (error) {
                console.error("[PosPrinter] ❌ Fiscal print error:", error);

                // Възстановяваме device
                this.device = originalDevice;

                // Fallback към стандартен принтер
                return await super.printHtml(el, { ...options, webPrintFallback: true });
            }
        }

        // Стандартен печат
        console.log("[PosPrinter] 🟢 Using standard print");
        return await super.printHtml(el, options);
    },
});
