#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # l10n_bg_property_account_receivable_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_account_receivable_id')
    # l10n_bg_property_account_payable_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_account_payable_id')
    # l10n_bg_property_account_expense_categ_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_account_expense_categ_id')
    # l10n_bg_property_account_income_categ_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_account_income_categ_id')
    # l10n_bg_expense_currency_exchange_account_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.expense_currency_exchange_account_id')
    # l10n_bg_income_currency_exchange_account_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.income_currency_exchange_account_id')
    # l10n_bg_property_tax_payable_account_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_tax_payable_account_id')
    # l10n_bg_property_tax_receivable_account_id = fields.Many2one(
    #     readonly=False,
    #     related='chart_template_id.property_tax_receivable_account_id')

    l10n_bg_uic = fields.Char(
        "Unique identification code", related="partner_id.l10n_bg_uic"
    )
    l10n_bg_uic_type = fields.Selection(
        string="Type of Bulgaria UID",
        related="partner_id.l10n_bg_uic_type",
        help="Choice type of Bulgaria UID.",
    )
    l10n_bg_departament_code = fields.Integer("Departament code")
    l10n_bg_tax_contact_id = fields.Many2one("res.partner", string="TAX Report creator")
    l10n_bg_odoo_compatible = fields.Boolean("TAX Odoo Compatible", default=True)

    def __init__(self, env, ids=(), prefetch_ids=()):
        super().__init__(env, ids=ids, prefetch_ids=prefetch_ids)
        env.cr.execute("SELECT column_name FROM information_schema.columns "
                       "WHERE table_name = 'res_company' AND column_name = 'l10n_bg_odoo_compatible'")
        if not env.cr.fetchone():
            env.cr.execute('ALTER TABLE res_company '
                           'ADD COLUMN l10n_bg_odoo_compatible boolean;')
            env.cr.execute("UPDATE res_company SET l10n_bg_odoo_compatible = True;")

    @api.depends("vat")
    def _onchange_vat(self):
        self.partner_id._check_l10n_bg_uic()
