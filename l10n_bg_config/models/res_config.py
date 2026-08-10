# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_l10n_bg_record = fields.Boolean(
        related="company_id.is_l10n_bg_record", readonly=False
    )
    l10n_bg_insignificant_value_threshold = fields.Monetary(
        related="company_id.l10n_bg_insignificant_value_threshold",
        readonly=False,
    )
    is_l10n_bg_multilanguage = fields.Json(
        related="company_id.is_l10n_bg_multilanguage", readonly=False
    )
    l10n_bg_kid_ids = fields.Many2many(
        related="company_id.l10n_bg_kid_ids", readonly=False
    )
    l10n_bg_kid_codes = fields.Char(
        related="company_id.l10n_bg_kid_codes", readonly=False
    )
    is_l10n_bg_multilanguage_text = fields.Text(
        string="Multilanguage Settings",
        compute="_compute_multilanguage_text"
    )

    module_currency_rate_update_bg_bnb = fields.Boolean(
        "Download currency rates from Bulgaria National Bank (OCA)",
        help="Central currency rates downloaded from National Bank of Bulgaria",
    )
    module_currency_rate_live_fix = fields.Boolean(
        "Live Currency Rate Fix (EE)",
        help="Live Currency Rate Fix for Bulgaria (EE) module",
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
    module_l10n_bg_report_vat = fields.Boolean(
        "Bulgaria - Tax Report  export files (OCA)",
        help="Add tax reports and exports files for Bulgaria base on OCA report engine",
    )
    l10n_bg_config_template =fields.Binary(related="company_id.l10n_bg_config_template", readonly=False)
    l10n_bg_key = fields.Char(related="company_id.partner_id.l10n_bg_key", readonly=False)
    enable_partner_api_key_view = fields.Boolean(
        string="Enable Partner API Key Shortcut",
        help="Enable the API Key shortcut (Shift+Alt+K) in partner form view",
        config_parameter="l10n_bg_config.enable_partner_api_key_view",
    )

    def set_values(self):
        super().set_values()
        # Activate/deactivate the view based on the setting
        view = self.env.ref('l10n_bg_config.view_res_partner_form_api_key', raise_if_not_found=False)
        if view:
            view.active = self.enable_partner_api_key_view

    def action_l10n_bg_open_installer(self):
        """Отваря многостъпковия воден инсталатор от секцията Settings,
        позициониран на вертикала за продължаване (resume)."""
        self.ensure_one()
        Vertical = self.env["l10n.bg.vertical"]
        start = Vertical._l10n_bg_resume_vertical()
        if not start:
            raise UserError(
                _("No installation verticals are configured.")
            )
        wizard = self.env["l10n.bg.vertical.wizard"].create(
            {"vertical_id": start.id}
        )
        return wizard._open()

    def action_l10n_bg_resolve_kid_codes(self):
        """Препраща към едноименния метод на текущата фирма."""
        self.ensure_one()
        return self.company_id.action_l10n_bg_resolve_kid_codes()

    @api.depends('company_id.is_l10n_bg_multilanguage')
    def _compute_multilanguage_text(self):
        for record in self:
            multilang_data = record.company_id.is_l10n_bg_multilanguage

            if multilang_data and isinstance(multilang_data, dict):
                # Форматиране на JSON за четимост
                record.is_l10n_bg_multilanguage_text = json.dumps(
                    multilang_data,
                    indent=4,
                    ensure_ascii=False
                )
            else:
                record.is_l10n_bg_multilanguage_text = "No data"
