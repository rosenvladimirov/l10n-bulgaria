from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_bg_is_customs_expense = fields.Boolean(
        string='Is Customs Expense',
        help='Check this if the product represents customs-related expense'
    )
