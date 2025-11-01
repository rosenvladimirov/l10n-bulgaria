/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PrinterService } from "@point_of_sale/app/printer/printer_service";
import { ErpNetFPPrinter } from "@l10n_bg_erp_net_fp/js/erp_net_fp_printer";

console.log("[PosPrinter] 🔧 Loading POS Fiscal Printer Extension...");

/**
 * Patch на PosStore за да catch-нем когато е ready
 */
patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        console.log("[PosPrinter] 🎯 PosStore is ready!");
        console.log("[PosPrinter] 📋 Session:", this.session);
        console.log("[PosPrinter] 📋 Config:", this.config);

        // Запазваме референция към POS store
        window.__fiscalPrinterPosStore = this;
    }
});

/**
 * Patch на PrinterService за добавяне на ErpNet.FP поддръжка
 */
patch(PrinterService.prototype, {
    setup(env, { renderer }) {
        super.setup(...arguments);

        this.fiscalPrinter = null;
        this.standardPrinter = this.device;

        console.log("[PosPrinter] 🚀 PrinterService.setup() called");

        // Стартираме инициализацията АСИНХРОННО
        setTimeout(() => {
            this._initializeFiscalPrinter(env).catch(err => {
                console.error("[PosPrinter] ❌ Error during initialization:", err);
            });
        }, 100);
    },

    /**
     * Инициализация на фискален принтер от session данните
     */
    async _initializeFiscalPrinter(env) {
        console.log("[PosPrinter] 🔄 Starting fiscal printer initialization...");

        // Чакаме PosStore да е готов
        let attempts = 0;
        while (!window.__fiscalPrinterPosStore && attempts < 100) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;

            if (attempts % 20 === 0) {
                console.log(`[PosPrinter] ⏳ Waiting for PosStore... (${attempts * 100}ms)`);
            }
        }

        const pos = window.__fiscalPrinterPosStore;

        if (!pos) {
            console.error("[PosPrinter] ❌ PosStore not available after timeout");
            return;
        }

        console.log("[PosPrinter] ✅ PosStore found!");
        console.log("[PosPrinter] 📋 Session:", pos.session);
        console.log("[PosPrinter] 📋 Config:", pos.config);

        // Фискалният принтер е в session.l10n_bg_fiscal_printer_id
        const fiscalPrinterId = pos.session?.l10n_bg_fiscal_printer_id;

        console.log("[PosPrinter] 🔍 Fiscal printer ID from session:", fiscalPrinterId);

        if (!fiscalPrinterId) {
            console.warn("[PosPrinter] ⚠️ No fiscal printer configured in session");
            return;
        }

        // Намираме конфигурацията на принтера
        const fiscalPrinterConfig = await this._findFiscalPrinterConfig(env, pos, fiscalPrinterId);

        if (!fiscalPrinterConfig) {
            console.error("[PosPrinter] ❌ Fiscal printer not found");
            return;
        }

        console.log("[PosPrinter] 🎯 Found ErpNet.FP fiscal printer:");
        console.log("[PosPrinter]    ID:", fiscalPrinterConfig.id);
        console.log("[PosPrinter]    Name:", fiscalPrinterConfig.name);
        console.log("[PosPrinter]    Host:", fiscalPrinterConfig.host);
        console.log("[PosPrinter]    Printer ID:", fiscalPrinterConfig.printer_id);
        console.log("[PosPrinter]    Connection mode:", fiscalPrinterConfig.connection_mode);

        // Проверка дали има нужните полета
        if (!fiscalPrinterConfig.host || !fiscalPrinterConfig.printer_id) {
            console.error("[PosPrinter] ❌ Fiscal printer config is incomplete");
            return;
        }

        try {
            this.fiscalPrinter = new ErpNetFPPrinter();
            this.fiscalPrinter.setup({
                baseUrl: fiscalPrinterConfig.host,
                printerId: fiscalPrinterConfig.printer_id,
                connectionMode: fiscalPrinterConfig.connection_mode,
                pos: pos,
            });

            console.log("[PosPrinter] ✅ ErpNet.FP fiscal printer initialized successfully!");

            if (env.services?.notification) {
                env.services.notification.add(
                    _t("Фискален принтер ErpNet.FP е готов"),
                    { type: "success" }
                );
            }
        } catch (error) {
            console.error("[PosPrinter] ❌ Error creating fiscal printer:", error);
        }
    },

    /**
     * Намира конфигурацията на фискалния принтер
     */
    async _findFiscalPrinterConfig(env, pos, fiscalPrinterId) {
        console.log("[PosPrinter] 🔍 Looking for fiscal printer config...");
        console.log("[PosPrinter]    Printer ID:", fiscalPrinterId);

        let printerId = fiscalPrinterId;

        // Ако е масив [id, name], вземаме id-то
        if (Array.isArray(fiscalPrinterId)) {
            printerId = fiscalPrinterId[0];
            console.log("[PosPrinter]    Extracted ID from array:", printerId);
        }

        // Опит 1: pos.models['fiscal.printer.device']
        if (pos.models?.['fiscal.printer.device']) {
            console.log("[PosPrinter] 🔍 Searching in pos.models...");
            const model = pos.models['fiscal.printer.device'];

            if (typeof model.get === 'function') {
                const config = model.get(printerId);
                if (config) {
                    console.log("[PosPrinter] ✅ Found in pos.models via .get()");
                    return config;
                }
            }

            if (typeof model.getAll === 'function') {
                const all = model.getAll();
                const config = all.find(p => p.id === printerId);
                if (config) {
                    console.log("[PosPrinter] ✅ Found in pos.models via .getAll()");
                    return config;
                }
            }
        }

        // Опит 2: pos.data
        if (pos.data?.models?.['fiscal.printer.device']) {
            console.log("[PosPrinter] 🔍 Searching in pos.data.models...");
            const records = pos.data.models['fiscal.printer.device'];

            if (Array.isArray(records)) {
                const config = records.find(p => p.id === printerId);
                if (config) {
                    console.log("[PosPrinter] ✅ Found in pos.data.models array");
                    return config;
                }
            } else if (typeof records.get === 'function') {
                const config = records.get(printerId);
                if (config) {
                    console.log("[PosPrinter] ✅ Found in pos.data.models via .get()");
                    return config;
                }
            }
        }

        // Опит 3: Директна RPC заявка
        console.log("[PosPrinter] 🔍 Not found in cache, fetching from server...");
        try {
            const orm = env.services.orm;
            const result = await orm.call('fiscal.printer.device', 'read', [[printerId]], {
                fields: ['id', 'name', 'host', 'printer_id', 'connection_mode']
            });

            if (result && result.length > 0) {
                console.log("[PosPrinter] ✅ Fetched from server");
                return result[0];
            }
        } catch (error) {
            console.error("[PosPrinter] ❌ Error fetching from server:", error);
        }

        console.error("[PosPrinter] ❌ Fiscal printer config not found anywhere");
        console.log("[PosPrinter] 💡 Available data:");
        console.log("[PosPrinter]    - pos.models:", Object.keys(pos.models || {}));
        console.log("[PosPrinter]    - pos.data:", pos.data);
        console.log("[PosPrinter]    - pos.data.models:", Object.keys(pos.data?.models || {}));

        return null;
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

        // Проверка дали трябва да използваме фискален принтер
        const shouldUseFiscal = this.fiscalPrinter && !options.kitchen && !options.skipFiscal;

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
                            _t("Грешка при фискален печат: ") + (result.message?.body || "Неизвестна грешка"),
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
                        _t("Фискален бон отпечатан") +
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

console.log("[PosPrinter] ✅ PrinterService patched successfully");
