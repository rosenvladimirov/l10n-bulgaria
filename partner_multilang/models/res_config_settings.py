# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    transliterate_names = fields.Boolean(
        related="company_id.transliterate_names",
        readonly=False,
        string="Transliterate names",
        help="Enable automatic transliteration of partner and company names."
    )
