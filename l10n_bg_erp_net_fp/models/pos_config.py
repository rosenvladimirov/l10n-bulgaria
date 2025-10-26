from odoo import models, fields, api, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    fiscal_printer_id = fields.Many2one(
        'fiscal.printer.device',
        string='Fiscal printer',
        domain=[('active', '=', True)],
        help='Fiscal printer for this POS terminal'
    )
    auto_fiscal_printing = fields.Boolean(
        'Automatic printing',
        default=True,
        help='Automatically print a fiscal voucher upon completion of an order'
    )
