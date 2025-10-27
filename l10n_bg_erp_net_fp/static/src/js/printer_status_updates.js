/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

/**
 * List controller за fiscal.printer.device
 * Добавя периодична проверка на статус
 */
export class FiscalPrinterListController extends ListController {
    setup() {
        super.setup();
        this.fiscalPrinterService = useService("fiscal_printer");
        this.orm = useService("orm");
        this.statusCheckInterval = null;

        onMounted(() => {
            this._startStatusPolling();
        });

        onWillUnmount(() => {
            this._stopStatusPolling();
        });
    }

    /**
     * Стартира периодична проверка на статуса на принтерите
     */
    _startStatusPolling() {
        // Проверка на всеки 30 секунди
        this.statusCheckInterval = setInterval(() => {
            this._checkAllPrintersStatus();
        }, 30000);

        // Веднага правим първа проверка
        this._checkAllPrintersStatus();
    }

    _stopStatusPolling() {
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
            this.statusCheckInterval = null;
        }
    }

    /**
     * Проверява статуса на всички принтери в списъка
     */
    async _checkAllPrintersStatus() {
        const records = this.model.root.records;

        for (const record of records) {
            const printerId = record.data.id;
            const printerName = record.data.name;

            // Изпращаме заявка за проверка (глобалният сервис ще я обработи)
            try {
                await this.orm.call(
                    'fiscal.printer.device',
                    'action_request_status',
                    [[printerId]]
                );
            } catch (error) {
                console.error(`Error requesting status for ${printerName}:`, error);
            }
        }
    }
}

// Регистрираме custom list view за fiscal.printer.device
export const fiscalPrinterListView = {
    ...listView,
    Controller: FiscalPrinterListController,
};

registry.category("views").add("fiscal_printer_status_list", fiscalPrinterListView);
