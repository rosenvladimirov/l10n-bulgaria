# models/pos_config.py
from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_bg_fiscal_printer_id = fields.Many2one(
        'fiscal.printer.device',
        string='Фискален принтер',
        help='Фискален принтер за тази POS конфигурация'
    )
    l10n_bg_auto_z_on_close = fields.Boolean(
        string='Автоматичен Z отчет при затваряне',
        default=True,
        help='Автоматично отпечатване на Z отчет при затваряне на сесията'
    )
