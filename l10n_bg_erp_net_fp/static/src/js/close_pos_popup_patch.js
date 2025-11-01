/** @odoo-module **/

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ErpNetFPPrinter } from "@l10n_bg_erp_net_fp/js/erp_net_fp_printer";

patch(ClosePosPopup.prototype, {

    /**
     * Получава или създава ErpNetFPPrinter инстанция
     */
    _getOrCreateFiscalPrinter() {
        const fiscalPrinterHost = this.pos.session?.l10n_bg_erp_net_fp_host;
        const fiscalPrinterId = this.pos.session?.l10n_bg_erp_net_fp_ip;

        if (!fiscalPrinterHost || !fiscalPrinterId) {
            console.warn("[ClosePosPopup] Fiscal printer not configured");
            return null;
        }

        // Създаваме нова инстанция
        return new ErpNetFPPrinter(this.env, {
            baseUrl: fiscalPrinterHost,
            printerId: fiscalPrinterId,
        });
    },

    /**
     * Печат на X отчет (междинен, без нулиране)
     */
    async printXReport() {
        console.log("[ClosePosPopup] 📊 X Report requested");

        const fiscalPrinter = this._getOrCreateFiscalPrinter();

        if (!fiscalPrinter) {
            this.env.services.notification.add(
                _t("Фискалният принтер не е конфигуриран"),
                { type: "warning" }
            );
            return;
        }

        try {
            // Показваме loader
            this.env.services.notification.add(
                _t("Генериране на X отчет..."),
                { type: "info" }
            );

            const result = await fiscalPrinter.printXReport();

            if (result.successful) {
                this.env.services.notification.add(
                    _t("X отчетът е отпечатан успешно"),
                    { type: "success" }
                );
            } else {
                throw new Error(result.message?.body || _t("Грешка при печат"));
            }
        } catch (error) {
            console.error("[ClosePosPopup] X Report error:", error);
            this.env.services.notification.add(
                _t("Грешка при X отчет: ") + error.message,
                { type: "danger", sticky: true }
            );
        }
    },

    /**
     * Печат на Z отчет (дневен фискален, с нулиране)
     */
    async printZReport() {
        console.log("[ClosePosPopup] 📊 Z Report requested");

        const fiscalPrinter = this._getOrCreateFiscalPrinter();

        if (!fiscalPrinter) {
            this.env.services.notification.add(
                _t("Фискалният принтер не е конфигуриран"),
                { type: "warning" }
            );
            return;
        }

        try {
            // Показваме loader
            this.env.services.notification.add(
                _t("Генериране на Z отчет..."),
                { type: "info" }
            );

            const result = await fiscalPrinter.printZReport();

            if (result.successful) {
                this.env.services.notification.add(
                    _t("Z отчетът е отпечатан успешно! Дневните данни са нулирани."),
                    { type: "success", sticky: true }
                );
            } else {
                throw new Error(result.message?.body || _t("Грешка при печат"));
            }
        } catch (error) {
            console.error("[ClosePosPopup] Z Report error:", error);
            this.env.services.notification.add(
                _t("Грешка при Z отчет: ") + error.message,
                { type: "danger", sticky: true }
            );
        }
    },

});
