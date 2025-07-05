from odoo import models, fields, api, _


class FiscalPrinterStatus(models.Model):
    _name = 'fiscal.printer.status'
    _description = 'Статус на фискален принтер'
    _order = 'create_date desc'

    printer_id = fields.Many2one('fiscal.printer.device', string='Фискален принтер', required=True, ondelete='cascade')
    status = fields.Char('Статус')
    error_message = fields.Char('Съобщение за грешка')
    create_date = fields.Datetime('Време на проверка', readonly=True)
    is_ready = fields.Boolean('Готов за работа')
    paper_available = fields.Boolean('Налична хартия')
    fiscal_memory_available = fields.Boolean('Налична фискална памет')
    document_number = fields.Char('Номер на последен документ')
    serial_number = fields.Char('Сериен номер')
    firmware_version = fields.Char('Версия на фърмуера')
