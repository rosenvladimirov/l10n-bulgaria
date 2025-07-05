from odoo import models, fields, api, _


class FiscalPrinterDevice(models.Model):
    _inherit = 'fiscal.printer.device'

    status_ids = fields.One2many('fiscal.printer.status', 'printer_id', string='Status history')
    current_status = fields.Char('Current status', compute='_compute_current_status', store=False)
    is_ready = fields.Boolean('Ready', compute='_compute_current_status', store=False)

    def _compute_current_status(self):
        for printer in self:
            last_status = printer.status_ids.sorted('create_date', reverse=True)[:1]
            printer.current_status = last_status.status if last_status else 'There is no information'
            printer.is_ready = last_status.is_ready if last_status else False

    def update_status(self):
        """Обновява статуса на принтера и изпраща notification през bus"""
        self.ensure_one()
        try:
            status_data = self.get_printer_status()

            status = self.env['fiscal.printer.status'].create({
                'printer_id': self.id,
                'status': status_data.get('status'),
                'error_message': status_data.get('errorMessage'),
                'is_ready': status_data.get('ok', False),
                'paper_available': status_data.get('paperAvailable', False),
                'fiscal_memory_available': status_data.get('fiscalMemoryAvailable', False),
                'document_number': status_data.get('documentNumber'),
                'serial_number': status_data.get('serialNumber'),
                'firmware_version': status_data.get('firmwareVersion')
            })

            # Подготвяне на данните за изпращане
            notification = {
                'type': 'printer_status_update',
                'printer_id': self.id,
                'name': self.name,
                'status': status_data.get('status'),
                'is_ready': status_data.get('ok', False),
                'error_message': status_data.get('errorMessage'),
                'last_update': fields.Datetime.now()
            }

            # Изпращане на notification през bus
            self.env['bus.bus']._sendone(
                'fiscal.printer.status',
                notification
            )

        except Exception as e:
            error_status = self.env['fiscal.printer.status'].create({
                'printer_id': self.id,
                'status': 'error',
                'error_message': str(e),
                'is_ready': False
            })

            # Изпращане на notification за грешка
            self.env['bus.bus']._sendone(
                'fiscal.printer.status',
                'printer_status_update',
                {
                    'type': 'printer_status_update',
                    'printer_id': self.id,
                    'name': self.name,
                    'status': 'error',
                    'is_ready': False,
                    'error_message': str(e),
                    'last_update': fields.Datetime.now()
                }
            )
