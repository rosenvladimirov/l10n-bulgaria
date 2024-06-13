# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_l10n_bg_record = fields.Boolean(compute="_check_is_l10n_bg_record", store=True)
    # l10n_bg_property_account_receivable_id = fields.Many2one(
    #     'account.account',
    #     related='chart_template_id.property_account_receivable_id')
    # l10n_bg_property_account_payable_id = fields.Many2one(
    #     'account.account',
    #     related='chart_template_id.property_account_payable_id')
    # l10n_bg_property_account_expense_categ_id = fields.Many2one(
    #     'account.account',
    #     related='chart_template_id.property_account_expense_categ_id')
    # l10n_bg_property_account_income_categ_id = fields.Many2one(
    #     'account.account',
    #     related='chart_template_id.property_account_income_categ_id')
    # l10n_bg_expense_currency_exchange_account_id = fields.Many2one(
    #     'account.account',
    #     related='chart_template_id.expense_currency_exchange_account_id')
    # l10n_bg_income_currency_exchange_account_id = fields.Many2one(
    #     'account.account',
    #     related='chart_template_id.income_currency_exchange_account_id')
    # l10n_bg_property_tax_payable_account_id = fields.Many2one(
    #     'account.account',
    #     related='chart_template_id.property_tax_payable_account_id')
    # l10n_bg_property_tax_receivable_account_id = fields.Many2one(
    #     'account.account',
    #     related='chart_template_id.property_tax_receivable_account_id')

    module_l10n_bg_tax_admin = fields.Boolean(
        "Bulgaria - Accounting tax",
        help="Provide all needed functionality for Bulgarian.\n"
        "Accounting and law documents.",
    )
    module_currency_rate_update_bg_bnb = fields.Boolean(
        "Download currency rates from Bulgaria National Bank",
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
    # module_l10n_bg_account_financial_report = fields.Boolean(
    #     'Bulgaria - Account Financial Reports',
    #     help='Provide all reports for Bulgarian accounting.'
    # )
    module_l10n_bg_intrastat_product = fields.Boolean(
        "Bulgaria - Intrastat Product Declaration",
        help="Provide Intrastat Product Declaration.",
    )
    module_partner_multilang = fields.Boolean(
        "Partner transliterate names",
        help="Transliterate partner, city, street names ISO9 and other",
    )
    module_l10n_bg_multilang = fields.Boolean(
        "Switch on multilanguage support",
        help="Change to multilingual support for fields without native configurations",
    )
    module_account_financial_forms = fields.Boolean(
        "TAX Audit forms",
        help="Account financial report base on tax administration forms for audit",
    )
    module_l10n_bg_uic_id_number = fields.Boolean(
        "Bulgarian multi register codes",
        help="Bulgarian registration codes base on OCA module partner_identification",
    )
    module_l10n_bg_coa_reports = fields.Boolean(
        "Bulgaria - Accounting tax reports",
        help="Provide all COA reports for Bulgarian.",
    )
    module_l10n_bg_vat_reports = fields.Boolean(
        "Bulgaria - Accounting VAT reports",
        help="Provide all VAT reports for Bulgarian - NRA.",
    )
    module_l10n_bg_intrastat = fields.Boolean(
        "Bulgaria - Intrastat",
        help="Generate XML files for Bulgaria intrastat",
    )
    module_l10n_bg_assets = fields.Boolean(
        "Bulgaria - Assets",
        help="Add rules for tax desperation base Bulgarian law",
    )

    # module_l10n_bg_account_voucher = fields.Boolean(
    #     'Bulgaria - Accounting voucher',
    #     help='This is the module to manage the Accounting Vouchers.\n'
    #     'Extend account voucher (tickets) to make simply invoices.'
    # )
    # module_l10n_bg_vat_period_gensoft = fields.Boolean(
    #     'Bulgaria - Use different period for VAT',
    #     help='Split vendor bill to use VAT credit in different period.'
    # )
    # module_l10n_bg_fleet_waybill = fields.Boolean(
    #     'Bulgaria - Vehicle Waybill',
    #     help='This is the module add waybill for Bulgaria with stock move.'
    # )
    # module_l10n_bg_hr_expense = fields.Boolean(
    #     'Bulgaria - Accounting Expense Tracker',
    #     help='This is the module to manage the Accounting Expense Tracker.'
    # )

    def _check_is_l10n_bg_record(self):
        return (
            self.company_id.chart_template_id.id
            == self.env.ref("l10n_bg.l10n_bg_chart_template").id
        )
