# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    company_country_id = fields.Many2one(
        "res.country",
        string="Company country",
        related="company_id.account_fiscal_country_id",
        readonly=True,
    )
    l10n_bg_intrastat_region_id = fields.Many2one(
        "account.intrastat.code",
        string="BG Company Intrastat Region",
        related="company_id.intrastat_region_id",
        domain="[('type', '=', 'region'), '|', ('country_id', '=', None), ('country_id', '=', company_country_id)]",
        readonly=False,
    )
