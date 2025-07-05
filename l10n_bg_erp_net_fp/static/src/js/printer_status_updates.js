odoo.define('fiscal_printer.PrinterStatusUpdates', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var BusService = require('bus.BusService');

    var PrinterListController = ListController.extend({
        init: function () {
            this._super.apply(this, arguments);
            this._startBusListener();
        },

        _startBusListener: function () {
            var self = this;
            this.call('bus_service', 'onNotification', this, function (notifications) {
                notifications.forEach(function (notification) {
                    if (notification[0] === 'fiscal.printer.status') {
                        var message = notification[1];
                        if (message.type === 'printer_status_update') {
                            self._handleStatusUpdate(message);
                        }
                    }
                });
            });
            this.call('bus_service', 'startPolling');
        },

        _handleStatusUpdate: function (data) {
            var self = this;
            // Намиране на реда в списъка и обновяване на данните
            var record = self.model.get(self.handle).data.find(
                function(r) {
                    return r.data.id === data.printer_id;
                }
            );

            if (record) {
                self.model.reload(record.id).then(function () {
                    self.renderer.updateRecord(record);
                });
            }
        },
    });

    var PrinterListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: PrinterListController,
        }),
    });

    viewRegistry.add('printer_status_list', PrinterListView);
});
