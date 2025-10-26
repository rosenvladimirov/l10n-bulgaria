# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class PosPrinter(models.Model):
    _inherit = 'pos.printer'

    printer_type = fields.Selection(selection_add=[
        ('erp_net_fp', 'BG ErpNET FP'),
    ])
    l10n_bg_fiscal_printer_id = fields.Many2one(
        'fiscal.printer.device',
        string='Fiscal printer',
        domain=[('active', '=', True)],
        help='Fiscal printer for this POS terminal'
    )
    l10n_bg_printer_id = fields.Char(
        related='l10n_bg_fiscal_printer_id.printer_id'
    )
    l10n_bg_proxy_ip = fields.Char(size=45, related='l10n_bg_fiscal_printer_id.host', store=True)

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result += ['l10n_bg_printer_id', 'l10n_bg_proxy_ip']
        return result
