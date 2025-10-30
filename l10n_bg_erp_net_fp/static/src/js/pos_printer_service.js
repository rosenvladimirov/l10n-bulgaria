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
    dependencies: ["hardware_proxy", "dialog", "renderer", "pos"],

    start(env, { hardware_proxy, dialog, renderer, pos }) {
        return {
            env,
            hardware_proxy,
            dialog,
            renderer,
            pos,
            fiscalPrinter: null,
            standardPrinter: hardware_proxy.printer,
            currentPrinter: hardware_proxy.printer,
            state: { isPrinting: false },

            /**
             * Инициализация на фискален принтер ако е конфигуриран
             */
            async _initializeFiscalPrinter() {
                if (!this.pos || !this.pos.config) {
                    return;
                }

                // Изчакваме POS да се зареди напълно
                await this.pos.ready;

                const printers = this.pos.orderPrinters || this.pos.printers || this.pos.config?.printers || [];
                const fiscalPrinterConfig = printers.find(
                    (p) => p.printer_type === "erp_net_fp" && p.l10n_bg_proxy_ip && p.l10n_bg_printer_id
                );

                if (fiscalPrinterConfig) {
                    this.fiscalPrinter = new ErpNetFPPrinter();
                    this.fiscalPrinter.setup({
                        baseUrl: fiscalPrinterConfig.l10n_bg_proxy_ip,
                        printerId: fiscalPrinterConfig.l10n_bg_printer_id,
                        pos: this.pos,
                    });
                    console.log("[PosPrinter] ErpNet.FP fiscal printer initialized");
                }
            },

            /**
             * Избор на правилния принтер според контекста
             */
            _selectPrinter(options = {}) {
                // Ако изрично е зadadeno fiscal
                if (options.fiscal && this.fiscalPrinter) {
                    return this.fiscalPrinter;
                }

                // Ако има фискален принтер И НЕ е kitchen order
                if (this.fiscalPrinter && !options.kitchen) {
                    return this.fiscalPrinter;
                }

                // Иначе стандартен принтер (IoT/ePOS)
                return this.standardPrinter;
            },

            /**
             * Главен метод за печат
             */
            async print(component, props, options = {}) {
                this.state.isPrinting = true;

                try {
                    // Рендерираме компонента в HTML
                    const el = await renderer.toHtml(component, props);

                    // Изчакваме всички изображения да се заредят
                    try {
                        await this._loadAllImages(el);
                    } catch (e) {
                        console.warn("Images could not be loaded:", e);
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

                console.log(`[PosPrinter] Using ${printerName} printer`);

                try {
                    // Фискален печат
                    if (selectedPrinter === this.fiscalPrinter) {
                        const result = await selectedPrinter.printReceipt(el);
                        if (!result.successful) {
                            throw result;
                        }
                        return true;
                    }

                    // Стандартен печат
                    if (this.standardPrinter && typeof this.standardPrinter.printReceipt === 'function') {
                        const result = await this.standardPrinter.printReceipt(el);
                        if (result && result.successful) {
                            return true;
                        }
                        if (result && !result.successful) {
                            throw result;
                        }
                    }

                    // Fallback към web print ако е разрешено
                    if (options.webPrintFallback) {
                        return this.printWeb(el);
                    }

                    return false;

                } catch (error) {
                    console.error("[PosPrinter] Print error:", error);
                    return await this._handlePrintError(error, el, options);
                }
            },

            /**
             * Обработка на грешки при печат
             */
            async _handlePrintError(error, el, options) {
                const isFiscalError = error.errorCode && error.errorCode.startsWith("ERPNET_FP");

                let message = error.message?.body || error.body || error.message || _t("Unknown error");
                let title = error.message?.title || error.title || _t("Printing error");

                // Ако е грешка от фискален принтер и имаме fallback
                if (isFiscalError && this.standardPrinter) {
                    message += "\n\n" + _t("Do you want to try standard printer or web print?");
                } else {
                    message += "\n\n" + _t("Do you want to print using the web printer?");
                }

                const confirmed = await ask(this.dialog, {
                    title: title,
                    body: message,
                });

                if (!confirmed) {
                    return false;
                }

                // Опит със стандартния принтер
                if (isFiscalError && this.standardPrinter) {
                    try {
                        this.currentPrinter = this.standardPrinter;
                        if (typeof this.standardPrinter.printReceipt === 'function') {
                            const result = await this.standardPrinter.printReceipt(el);
                            if (result && result.successful) {
                                return true;
                            }
                        }
                    } catch (fallbackError) {
                        console.error("[PosPrinter] Standard printer also failed:", fallbackError);
                    }
                }

                // Последна опция - web print
                await new Promise(requestAnimationFrame);
                return this.printWeb(el);
            },

            /**
             * Web print fallback
             */
            printWeb(el) {
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
                    console.error("[PosPrinter] Web print failed:", error);

                    this.dialog.add(AlertDialog, {
                        title: _t("Printing not supported"),
                        body: _t("Web printing is not available in this browser. Please use an IoT Box or enable printer access."),
                    });

                    return false;
                }
            },

            /**
             * Отваряне на касова чекмедже
             */
            async openCashbox() {
                // Опит с фискален принтер
                if (this.fiscalPrinter) {
                    try {
                        console.log("[PosPrinter] Opening cashbox via fiscal printer");
                        const result = await this.fiscalPrinter.openCashbox();
                        if (result) {
                            return true;
                        }
                    } catch (error) {
                        console.error("[PosPrinter] Fiscal cashbox error:", error);
                    }
                }

                // Fallback към стандартен принтер
                if (this.standardPrinter && typeof this.standardPrinter.openCashbox === 'function') {
                    console.log("[PosPrinter] Opening cashbox via standard printer");
                    return await this.standardPrinter.openCashbox();
                }

                console.warn("[PosPrinter] No cashbox support available");
                return false;
            },

            /**
             * Проверка дали има наличен принтер
             */
            is() {
                return Boolean(this.currentPrinter || this.standardPrinter || this.fiscalPrinter);
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
