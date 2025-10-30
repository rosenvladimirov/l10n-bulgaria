import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { PrinterService } from "@point_of_sale/app/printer/printer_service";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { ErpNetFPPrinter } from "@point_of_sale/app/printer/erp_net_fp_printer";

export const posPrinterService = {
    dependencies: ["hardware_proxy", "dialog", "renderer", "pos"],
    start(env, { hardware_proxy, dialog, renderer, pos }) {
        return new PosPrinterService(env, { hardware_proxy, dialog, renderer, pos });
    },
};
export class PosPrinterService extends PrinterService {
    constructor(...args) {
        super(...args);
        this.setup(...args);
    }
    setup(env, { hardware_proxy, dialog, renderer, pos }) {
        super.setup(...arguments);
        this.renderer = renderer;
        this.hardware_proxy = hardware_proxy;
        this.dialog = dialog;
        this.pos = pos;
        this.fiscalPrinter = null;

        // Стандартен принтер от hardware_proxy (може да е IoT, ePOS и т.н.)
        this.standardPrinter = hardware_proxy.printer;

        // По подразбиране използваме стандартния принтер
        this.device = this.standardPrinter;

        // Инициализираме фискален принтер ако е конфигуриран
        this._initializeFiscalPrinter();
    }

    /**
     * Инициализация на фискален принтер ако е конфигуриран
     */
    _initializeFiscalPrinter() {
        const pos = this.pos;
        if (!pos || !pos.config) {
            return;
        }

        const printers = pos.orderPrinters || pos.printers || pos.config?.printers || [];
        const fiscalPrinterConfig = printers.find(
            (p) =>
                p.printer_type === "erp_net_fp" &&
                p.l10n_bg_proxy_ip &&
                p.l10n_bg_printer_id
        );

        if (fiscalPrinterConfig) {
            this.fiscalPrinter = new ErpNetFPPrinter();
            this.fiscalPrinter.setup({
                baseUrl: fiscalPrinterConfig.l10n_bg_proxy_ip,
                printerId: fiscalPrinterConfig.l10n_bg_printer_id,
                pos: pos,
            });
            console.log("ErpNet.FP fiscal printer initialized");
        }
    }

    /**
     * Избор на правилния принтер според контекста
     */
    _selectPrinter(options = {}) {
        // Ако изрично е зададено да се използва фискален принтер
        if (options.fiscal && this.fiscalPrinter) {
            return this.fiscalPrinter;
        }

        // Ако има фискален принтер И печатаме касов бон (не kitchen order)
        if (this.fiscalPrinter && !options.kitchen) {
            return this.fiscalPrinter;
        }

        // В останалите случаи използваме стандартния принтер
        // (IoT Box, ePOS, или каквото е конфигурирано)
        return this.standardPrinter;
    }

    printWeb() {
        try {
            return super.printWeb(...arguments);
        } catch {
            this.dialog.add(AlertDialog, {
                title: _t("Printing is not supported on some browsers"),
                body: _t("It is possible to print your tickets by making use of an IoT Box."),
            });
            return false;
        }
    }

    /**
     * @override
     * Интелигентен избор на принтер преди печат
     */
    async printHtml(el, options = {}) {
        // Избираме правилния принтер според контекста
        const selectedPrinter = this._selectPrinter(options);
        this.setPrinter(selectedPrinter);

        const printerName = selectedPrinter === this.fiscalPrinter
            ? "ErpNet.FP Fiscal"
            : "Standard (IoT/ePOS)";

        console.log(`[PosPrinter] Using ${printerName} printer for printing`);

        try {
            return await super.printHtml(el, options);
        } catch (error) {
            return this.printHtmlAlternative(error, el, options);
        }
    }

    /**
     * Fallback при грешка - опция за web print
     */
    async printHtmlAlternative(error, ...printArguments) {
        if (error.body === undefined) {
            console.error("An unknown error occured in printHtml:", error);
        }

        const isFiscalError = error.errorCode && error.errorCode.startsWith("ERPNET_FP");

        let confirmMessage = _t("Do you want to print using the web printer? ");

        // Ако грешката е от фискален принтер и имаме стандартен принтер като fallback
        if (isFiscalError && this.standardPrinter) {
            confirmMessage = _t(
                "Fiscal printer failed. Do you want to try standard printer or web print? "
            );
        }

        const confirmed = await ask(this.dialog, {
            title: error.title || _t("Printing error"),
            body: (error.body ?? "") + confirmMessage,
        });

        if (confirmed) {
            // Опит със стандартния принтер ако грешката е от фискалния
            if (isFiscalError && this.standardPrinter) {
                try {
                    this.setPrinter(this.standardPrinter);
                    return await super.printHtml(...printArguments);
                } catch (fallbackError) {
                    console.error("Fallback to standard printer also failed:", fallbackError);
                }
            }

            // Последна опция - web print
            await new Promise(requestAnimationFrame);
            this.printWeb(...printArguments);
        }
    }

    /**
     * @override
     * Отваряне на касова чекмедже
     * Приоритет: Фискален принтер -> Стандартен принтер
     */
    async openCashbox() {
        // Първо опит с фискален принтер ако има
        if (this.fiscalPrinter) {
            try {
                console.log("[PosPrinter] Opening cashbox via fiscal printer");
                const result = await this.fiscalPrinter.openCashbox();
                if (result) {
                    return true;
                }
            } catch (error) {
                console.error("Error opening cashbox via fiscal printer:", error);
            }
        }

        // Fallback към стандартен принтер (IoT Box и т.н.)
        if (this.standardPrinter && this.standardPrinter.openCashbox) {
            console.log("[PosPrinter] Opening cashbox via standard printer");
            return await this.standardPrinter.openCashbox();
        }

        console.warn("[PosPrinter] No cashbox support available");
        return false;
    }
}

registry.category("services").add("printer", posPrinterService);
