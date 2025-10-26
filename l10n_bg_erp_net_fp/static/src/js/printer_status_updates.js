/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, onMounted } from "@odoo/owl";

/**
 * Real-time обновяване на статус на фискални принтери
 * Използва се в backend list view на fiscal.printer.device
 */
export class FiscalPrinterListController extends ListController {
    setup() {
        super.setup();
        this.busService = useService("bus_service");

        onWillStart(async () => {
            await this._subscribeToBus();
        });

        onMounted(() => {
            this._addBusListener();
        });
    }

    async _subscribeToBus() {
        // Абонираме се за канала за статуси на принтери
        if (this.busService) {
            this.busService.addChannel("fiscal.printer.status");
        }
    }

    _addBusListener() {
        if (this.busService) {
            this.busService.addEventListener(
                "notification",
                this._onBusNotification.bind(this)
            );
        }
    }

    _onBusNotification({ detail: notifications }) {
        for (const notification of notifications) {
            const { type, payload } = notification;

            if (type === "fiscal.printer.status" && payload.type === "printer_status_update") {
                this._handleStatusUpdate(payload);
            }
        }
    }

    async _handleStatusUpdate(data) {
        // Показваме notification за промяна
        this.env.services.notification.add(
            `Принтер ${data.name}: ${data.status}`,
            {
                type: data.is_ready ? "success" : "warning",
                timeout: 3000,
            }
        );

        // Опреснявяме списъка
        await this.model.root.load();
        this.render();
    }
}

// Регистрираме custom list view за fiscal.printer.device
export const fiscalPrinterListView = {
    ...listView,
    Controller: FiscalPrinterListController,
};

registry.category("views").add("fiscal_printer_status_list", fiscalPrinterListView);
