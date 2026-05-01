/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { DatecsPMPrinter } from "@l10n_bg_fiscal_printer_datecs_pm/js/datecs_pm_printer";

/**
 * Patch ClosePosPopup — adds X/Z report buttons (rendered by the
 * companion XML inheritance template) and wires them to the device.
 *
 * Sibling reference:
 *   l10n_bg_erp_net_fp/static/src/js/close_pos_popup_patch.js
 *   l10n_bg_erp_net_fp/static/src/xml/pos_close_popup_template.xml
 */
patch(ClosePosPopup.prototype, {
    _l10nBgFpDatecsGetPrinter() {
        const session = this.pos.session;
        const proxyUrl = session?.l10n_bg_fp_datecs_proxy_url;
        const printerId = session?.l10n_bg_fp_datecs_printer_id;
        if (!proxyUrl || !printerId) return null;
        return new DatecsPMPrinter(this.env, {
            proxyUrl,
            printerId,
            posConfigId: this.pos.config?.id,
            sessionId: session.id,
        });
    },

    async printDatecsXReport() {
        const printer = this._l10nBgFpDatecsGetPrinter();
        if (!printer) {
            this.env.services.notification.add(
                _t("Datecs PM device not configured"),
                { type: "warning" },
            );
            return;
        }
        try {
            this.env.services.notification.add(
                _t("Generating X report…"),
                { type: "info" },
            );
            const result = await printer.printXReport();
            if (result?.ok) {
                this.env.services.notification.add(
                    _t("X report printed (#%(n)s)", {
                        n: result.n_rep || "?",
                    }),
                    { type: "success" },
                );
            } else {
                throw new Error(result?.error || _t("Unknown error"));
            }
        } catch (error) {
            this.env.services.notification.add(
                _t("X report error: ") + error.message,
                { type: "danger", sticky: true },
            );
        }
    },

    async printDatecsZReport() {
        const printer = this._l10nBgFpDatecsGetPrinter();
        if (!printer) {
            this.env.services.notification.add(
                _t("Datecs PM device not configured"),
                { type: "warning" },
            );
            return;
        }
        try {
            this.env.services.notification.add(
                _t("Generating Z report…"),
                { type: "info" },
            );
            const result = await printer.printZReport();
            if (result?.ok) {
                this.env.services.notification.add(
                    _t(
                        "Z report printed (#%(n)s) — daily totals reset.",
                        { n: result.n_rep || "?" },
                    ),
                    { type: "success", sticky: true },
                );
            } else {
                throw new Error(result?.error || _t("Unknown error"));
            }
        } catch (error) {
            this.env.services.notification.add(
                _t("Z report error: ") + error.message,
                { type: "danger", sticky: true },
            );
        }
    },
});
