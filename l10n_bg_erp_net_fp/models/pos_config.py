# models/pos_config.py
from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_bg_fiscal_printer_id = fields.Many2one(
        'fiscal.printer.device',
        string='Fiscal printer',
        help='Fiscal printer for this POS configuration'
    )
    l10n_bg_auto_z_on_close = fields.Boolean(
        string='Automatic Z report on closing',
        default=True,
        help='Automatic printing of Z report on session close'
    )
    l10n_bg_erp_net_fp_ip = fields.Char(
        'ErpNet.FP IP',
        compute='_compute_l10n_bg_erp_net_fp_ip',
        store=True
    )
    l10n_bg_erp_net_fp_host = fields.Char(
        'ErpNet.FP Host',
        compute='_compute_l10n_bg_erp_net_fp_host',
        store=True
    )

    @api.depends('l10n_bg_fiscal_printer_id', 'l10n_bg_fiscal_printer_id.host')
    def _compute_l10n_bg_erp_net_fp_ip(self):
        for config in self:
            config.l10n_bg_erp_net_fp_ip = config.l10n_bg_fiscal_printer_id.printer_id


    @api.depends('l10n_bg_fiscal_printer_id', 'l10n_bg_fiscal_printer_id.printer_id')
    def _compute_l10n_bg_erp_net_fp_host(self):
        for config in self:
            config.l10n_bg_erp_net_fp_host = config.l10n_bg_fiscal_printer_id.host
