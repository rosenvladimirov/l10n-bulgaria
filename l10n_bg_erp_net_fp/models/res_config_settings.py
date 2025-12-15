from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_bg_fiscal_printer_id = fields.Many2one(
        related='pos_config_id.l10n_bg_fiscal_printer_id',
        readonly=False,
        string='Fiscal printer'
    )

    l10n_bg_auto_z_on_close = fields.Boolean(
        related='pos_config_id.l10n_bg_auto_z_on_close',
        readonly=False,
        string='Automatic Z report'
    )
