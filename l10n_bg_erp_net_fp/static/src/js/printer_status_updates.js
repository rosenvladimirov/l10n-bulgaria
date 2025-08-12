/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

export class PrinterListController extends ListController {
    setup() {
        super.setup();
        this._startBusListener();
    }

    _startBusListener() {
        const busService = this.env.services.bus_service;
        if (busService) {
            busService.addEventListener('notification', this._onBusNotification.bind(this));
            busService.startPolling();
        }
    }

    _onBusNotification(notifications) {
        for (const notification of notifications) {
            if (notification.type === 'fiscal.printer.status') {
                const message = notification.payload;
                if (message.type === 'printer_status_update') {
                    this._handleStatusUpdate(message);
                }
            }
        }
    }

    async _handleStatusUpdate(data) {
        // Намиране на реда в списъка и обновяване на данните
        const records = this.model.root.records;
        const record = records.find(r => r.resId === data.printer_id);

        if (record) {
            await this.model.root.load();
            this.render();
        }
    }
}

export const printerListView = {
    ...listView,
    Controller: PrinterListController,
};

registry.category("views").add("printer_status_list", printerListView);
