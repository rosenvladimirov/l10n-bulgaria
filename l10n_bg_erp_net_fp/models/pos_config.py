from odoo import models, fields, api, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    fiscal_printer_id = fields.Many2one(
        'fiscal.printer.device',
        string='Фискален принтер',
        domain=[('active', '=', True)],
        help='Фискален принтер за този POS терминал'
    )
    auto_fiscal_printing = fields.Boolean(
        'Автоматичен печат',
        default=True,
        help='Автоматично отпечатване на фискален бон при приключване на поръчка'
    )
