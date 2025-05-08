# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api
from .l10n_bg_config_mixin import generate_encryption_keys


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_l10n_bg_record = fields.Boolean(
        related="company_id.is_l10n_bg_record", readonly=False
    )
    is_l10n_bg_multilanguage = fields.Json(
        related="company_id.is_l10n_bg_multilanguage", readonly=False
    )
    module_currency_rate_update_bg_bnb = fields.Boolean(
        "Download currency rates from Bulgaria National Bank (OCA)",
        help="Central currency rates downloaded from National Bank of Bulgaria",
    )
    module_l10n_bg_city = fields.Boolean(
        "Upload Bulgaria city",
        help="Upload cites, municipalities, states, villages and manastiries",
    )
    module_l10n_bg_address_extended = fields.Boolean(
        "Additional data in address", help="Additional data in address like "
    )
    module_l10n_bg_tax_offices = fields.Boolean(
        "NRA Bulgaria, tax offices and departments",
        help="Address and department of NRA Bulgaria added like partners"
        " to use when make a payment ot taxes.",
    )
    module_l10n_bg_intrastat_product = fields.Boolean(
        "Bulgaria - Intrastat Product Declaration",
        help="Provide Intrastat Product Declaration. (OCA)",
    )
    module_partner_multilang = fields.Boolean(
        "Partner transliterate names",
        help="Transliterate partner, city, street names ISO9 and other",
    )
    module_l10n_bg_multilang = fields.Boolean(
        "Switch on multilanguage support",
        help="Change to multilingual support for fields without native configurations",
    )
    module_l10n_bg_uic_id_number = fields.Boolean(
        "Bulgarian multi register codes",
        help="Bulgarian registration codes base on OCA module partner_identification",
    )
    module_l10n_bg_reports_audit = fields.Boolean(
        "Bulgaria - Accounting TAX Audit reports",
        help="Provide base for Accounting TAX Audit reports for Bulgarian - NRA.",
    )
    module_l10n_bg_intrastat = fields.Boolean(
        "Bulgaria - Intrastat",
        help="Generate XML files for Bulgaria intrastat (EE)",
    )
    module_l10n_bg_assets = fields.Boolean(
        "Bulgaria - Assets",
        help="Add rules for tax desperation base Bulgarian law (EE)",
    )
    module_l10n_bg_report_theme = fields.Boolean(
        "Bulgaria - Report Theme",
        help="Add theme for Bulgaria reports",
    )
    module_l10n_bg_vat_reports = fields.Boolean(
        "Bulgaria - VAT Reports export files (EE)",
        help="Add VAT reports  and exports files for Bulgaria base on EE report engine",
    )
    module_l10n_bg_tax_report = fields.Boolean(
        "Bulgaria - Tax Report  export files (OCA)",
        help="Add tax reports and exports files for Bulgaria base on OCA report engine",
    )
    l10n_bg_config_template =fields.Binary(related="company_id.l10n_bg_config_template", readonly=False)
    l10n_bg_key = fields.Char(related="company_id.partner_id.l10n_bg_key", readonly=False)

    @api.onchange("l10n_bg_key")
    def on_change_l10n_bg_key(self):
        for record in self:
            key2 = record.l10n_bg_key
            company_id = record.company_id
            company_id.partner_id.ref = generate_encryption_keys(company_id.partner_id.l10n_bg_uic, key2)
