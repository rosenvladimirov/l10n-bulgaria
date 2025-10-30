/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { ErpNetFPPrinter } from "@l10n_bg_erp_net_fp/js/erp_net_fp_printer";

/**
 * POS Printer Service with Fiscal Printer Support
 * Заменя стандартния printer service с интелигентен избор
 */
export const posPrinterService = {
    dependencies: ["hardware_proxy", "dialog", "renderer", "pos", "notification"],

    start(env, { hardware_proxy, dialog, renderer, pos, notification }) {
        return {
            env,
            hardware_proxy,
            dialog,
            renderer,
            pos,
            notification,
            fiscalPrinter: null,
            standardPrinter: hardware_proxy.printer,
            currentPrinter: hardware_proxy.printer,
            state: { isPrinting: false },

            /**
             * Инициализация на фискален принтер ако е конфигуриран
             */
            async _initializeFiscalPrinter() {
                console.log("[PosPrinter] Initializing fiscal printer...");

                if (!this.pos || !this.pos.config) {
                    console.warn("[PosPrinter] POS or config not available");
                    return;
                }

                // Изчакваме POS да се зареди напълно
                if (this.pos.ready) {
                    await this.pos.ready;
                }

                const printers = this.pos.orderPrinters || this.pos.printers || this.pos.config?.printers || [];
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
                        pos: this.pos,
                    });

                    console.log("[PosPrinter] ✅ ErpNet.FP fiscal printer initialized successfully!");
                    console.log(`[PosPrinter] Base URL: ${fiscalPrinterConfig.l10n_bg_proxy_ip}`);
                    console.log(`[PosPrinter] Printer ID: ${fiscalPrinterConfig.l10n_bg_printer_id}`);

                    // Показваме notification
                    this.notification.add(
                        _t("Fiscal printer ErpNet.FP initialized successfully"),
                        { type: "success" }
                    );
                } else {
                    console.warn("[PosPrinter] ⚠️ No fiscal printer configured!");
                    console.log("[PosPrinter] Available printer types:", printers.map(p => p.printer_type));
                }
            },

            /**
             * Избор на правилния принтер според контекста
             */
            _selectPrinter(options = {}) {
                // Debug информация
                console.log("[PosPrinter] Selecting printer...");
                console.log("[PosPrinter] Options:", options);
                console.log("[PosPrinter] Fiscal printer available:", !!this.fiscalPrinter);
                console.log("[PosPrinter] Standard printer available:", !!this.standardPrinter);

                // Ако изрично е зadadeno fiscal
                if (options.fiscal && this.fiscalPrinter) {
                    console.log("[PosPrinter] ✅ Selected: FISCAL (explicit)");
                    return this.fiscalPrinter;
                }

                // Ако има фискален принтер И НЕ е kitchen order
                if (this.fiscalPrinter && !options.kitchen) {
                    console.log("[PosPrinter] ✅ Selected: FISCAL (default for receipts)");
                    return this.fiscalPrinter;
                }

                // Иначе стандартен принтер (IoT/ePOS)
                console.log("[PosPrinter] ✅ Selected: STANDARD (IoT/ePOS)");
                return this.standardPrinter;
            },

            /**
             * Главен метод за печат
             */
            async print(component, props, options = {}) {
                console.log("[PosPrinter] 🖨️ Print request started");
                console.log("[PosPrinter] Component:", component);
                console.log("[PosPrinter] Options:", options);

                this.state.isPrinting = true;

                try {
                    // Рендерираме компонента в HTML
                    const el = await renderer.toHtml(component, props);

                    // Изчакваме всички изображения да се заредят
                    try {
                        await this._loadAllImages(el);
                    } catch (e) {
                        console.warn("[PosPrinter] Images could not be loaded:", e);
                    }

                    // Печатаме
                    return await this.printHtml(el, { ...options, component, props });

                } finally {
                    this.state.isPrinting = false;
                }
            },

            /**
             * Печат на HTML съдържание
             */
            async printHtml(el, options = {}) {
                const selectedPrinter = this._selectPrinter(options);
                this.currentPrinter = selectedPrinter;

                const printerName = selectedPrinter === this.fiscalPrinter
                    ? "ErpNet.FP Fiscal"
                    : "Standard (IoT/ePOS)";

                console.log(`[PosPrinter] 📄 Printing with: ${printerName}`);

                // Показваме notification
                this.notification.add(
                    _t(`Printing with ${printerName}...`),
                    { type: "info" }
                );

                try {
                    // Фискален печат
                    if (selectedPrinter === this.fiscalPrinter) {
                        console.log("[PosPrinter] 🔵 Starting FISCAL print...");

                        const result = await selectedPrinter.printReceipt(el);

                        console.log("[PosPrinter] Fiscal print result:", result);

                        if (!result.successful) {
                            console.error("[PosPrinter] ❌ FISCAL PRINT FAILED:", result);

                            // Показваме грешка
                            this.notification.add(
                                _t("Fiscal printer error: ") + (result.message?.body || result.message?.title || "Unknown error"),
                                { type: "danger" }
                            );

                            throw result;
                        }

                        console.log("[PosPrinter] ✅ FISCAL PRINT SUCCESS!");

                        // Показваме успех
                        this.notification.add(
                            _t("Fiscal receipt printed successfully") +
                            (result.fiscalData?.receiptNumber ? ` №${result.fiscalData.receiptNumber}` : ""),
                            { type: "success" }
                        );

                        return true;
                    }

                    // Стандартен печат
                    console.log("[PosPrinter] 🟢 Starting STANDARD print...");

                    if (this.standardPrinter && typeof this.standardPrinter.printReceipt === 'function') {
                        const result = await this.standardPrinter.printReceipt(el);

                        console.log("[PosPrinter] Standard print result:", result);

                        if (result && result.successful) {
                            console.log("[PosPrinter] ✅ STANDARD PRINT SUCCESS!");
                            return true;
                        }
                        if (result && !result.successful) {
                            console.error("[PosPrinter] ❌ STANDARD PRINT FAILED:", result);
                            throw result;
                        }
                    }

                    // Fallback към web print ако е разрешено
                    if (options.webPrintFallback) {
                        console.log("[PosPrinter] 🌐 Falling back to WEB PRINT...");

                        this.notification.add(
                            _t("No printer available, using web print..."),
                            { type: "warning" }
                        );

                        return this.printWeb(el);
                    }

                    console.warn("[PosPrinter] ⚠️ No print method available!");
                    return false;

                } catch (error) {
                    console.error("[PosPrinter] ❌ PRINT ERROR:", error);
                    return await this._handlePrintError(error, el, options);
                }
            },

            /**
             * Обработка на грешки при печат
             */
            async _handlePrintError(error, el, options) {
                const isFiscalError = error.errorCode && error.errorCode.startsWith("ERPNET_FP");

                console.log("[PosPrinter] Handling error...");
                console.log("[PosPrinter] Is fiscal error:", isFiscalError);
                console.log("[PosPrinter] Error:", error);

                let message = error.message?.body || error.body || error.message || _t("Unknown error");
                let title = error.message?.title || error.title || _t("Printing error");

                // Специално съобщение за фискален принтер
                if (isFiscalError) {
                    message = `⚠️ ФИСКАЛЕН ПРИНТЕР ГРЕШКА ⚠️\n\n${message}\n\n`;

                    if (this.standardPrinter) {
                        message += _t("Искате ли да опитате със стандартния принтер или web печат?");
                    } else {
                        message += _t("Искате ли да опитате с web печат?");
                    }

                    // Показваме notification
                    this.notification.add(
                        _t("Fiscal printer failed: ") + (error.message?.body || error.body || "Connection error"),
                        { type: "danger" }
                    );
                } else {
                    message += "\n\n" + _t("Искате ли да печатате с web принтера?");
                }

                const confirmed = await ask(this.dialog, {
                    title: title,
                    body: message,
                });

                if (!confirmed) {
                    console.log("[PosPrinter] User cancelled print");
                    return false;
                }

                // Опит със стандартния принтер
                if (isFiscalError && this.standardPrinter) {
                    try {
                        console.log("[PosPrinter] Trying standard printer as fallback...");

                        this.notification.add(
                            _t("Trying standard printer..."),
                            { type: "info" }
                        );

                        this.currentPrinter = this.standardPrinter;
                        if (typeof this.standardPrinter.printReceipt === 'function') {
                            const result = await this.standardPrinter.printReceipt(el);
                            if (result && result.successful) {
                                console.log("[PosPrinter] ✅ Standard printer SUCCESS!");

                                this.notification.add(
                                    _t("Printed with standard printer"),
                                    { type: "success" }
                                );

                                return true;
                            }
                        }
                    } catch (fallbackError) {
                        console.error("[PosPrinter] Standard printer also failed:", fallbackError);
                    }
                }

                // Последна опция - web print
                console.log("[PosPrinter] Using web print as last resort...");

                this.notification.add(
                    _t("Using web print..."),
                    { type: "warning" }
                );

                await new Promise(requestAnimationFrame);
                return this.printWeb(el);
            },

            /**
             * Web print fallback
             */
            printWeb(el) {
                console.log("[PosPrinter] 🌐 Web print started");

                try {
                    if (!window.print) {
                        throw new Error("Web printing not supported");
                    }

                    // Използваме renderer за web print ако е наличен
                    if (renderer && typeof renderer.whenMounted === 'function') {
                        renderer.whenMounted({ el, callback: window.print });
                        return true;
                    }

                    // Fallback - директен печат
                    const printWindow = window.open('', '_blank');
                    if (!printWindow) {
                        throw new Error("Could not open print window");
                    }

                    printWindow.document.write(`
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Print Receipt</title>
                            <style>
                                body { margin: 0; padding: 20px; font-family: monospace; }
                                @media print {
                                    body { margin: 0; padding: 0; }
                                }
                            </style>
                        </head>
                        <body>${el.outerHTML || el.innerHTML || el}</body>
                        </html>
                    `);

                    printWindow.document.close();
                    printWindow.focus();

                    setTimeout(() => {
                        printWindow.print();
                        printWindow.close();
                    }, 250);

                    return true;

                } catch (error) {
                    console.error("[PosPrinter] ❌ Web print failed:", error);

                    this.dialog.add(AlertDialog, {
                        title: _t("Печатът не се поддържа"),
                        body: _t("Web печат не е наличен в този браузър. Моля използвайте IoT Box или разрешете достъп до принтер."),
                    });

                    return false;
                }
            },

            /**
             * Отваряне на касова чекмедже
             */
            async openCashbox() {
                console.log("[PosPrinter] 💰 Opening cashbox...");

                // Опит с фискален принтер
                if (this.fiscalPrinter) {
                    try {
                        console.log("[PosPrinter] Trying fiscal printer cashbox...");
                        const result = await this.fiscalPrinter.openCashbox();
                        if (result) {
                            console.log("[PosPrinter] ✅ Cashbox opened via fiscal printer");
                            return true;
                        }
                    } catch (error) {
                        console.error("[PosPrinter] Fiscal cashbox error:", error);
                    }
                }

                // Fallback към стандартен принтер
                if (this.standardPrinter && typeof this.standardPrinter.openCashbox === 'function') {
                    console.log("[PosPrinter] Trying standard printer cashbox...");
                    const result = await this.standardPrinter.openCashbox();
                    console.log("[PosPrinter] ✅ Cashbox opened via standard printer");
                    return result;
                }

                console.warn("[PosPrinter] ⚠️ No cashbox support available");
                return false;
            },

            /**
             * Проверка дали има наличен принтер
             */
            is() {
                const available = Boolean(this.currentPrinter || this.standardPrinter || this.fiscalPrinter);
                console.log("[PosPrinter] Printer available:", available);
                return available;
            },

            /**
             * Зарежда всички изображения в HTML елемент
             */
            async _loadAllImages(el) {
                const images = el.querySelectorAll('img');
                const promises = Array.from(images).map(img => {
                    return new Promise((resolve, reject) => {
                        if (img.complete) {
                            resolve();
                        } else {
                            img.onload = resolve;
                            img.onerror = reject;
                            setTimeout(reject, 5000); // Timeout след 5 сек
                        }
                    });
                });
                return Promise.all(promises);
            }
        };
    },
};

// Презаписваме стандартния printer service
registry.category("services").add("printer", posPrinterService, { force: true });
