from odoo import models, fields, api, _


class FiscalPrinterStatus(models.Model):
    _name = 'fiscal.printer.status'
    _description = 'Fiscal Printer Status'
    _order = 'create_date desc'

    printer_id = fields.Many2one(
        'fiscal.printer.device',
        string='Fiscal printer',
        required=True,
        ondelete='cascade',
        index=True
    )
    status = fields.Char('Status', index=True)
    error_message = fields.Text('Error message')
    create_date = fields.Datetime('Check time', readonly=True, index=True)
    is_ready = fields.Boolean('Ready', index=True)
    paper_available = fields.Boolean('Paper available')
    fiscal_memory_available = fields.Boolean('Fiscal memory available')
    document_number = fields.Char('Last document number')
    serial_number = fields.Char('Serial number')
    firmware_version = fields.Char('Firmware version')
