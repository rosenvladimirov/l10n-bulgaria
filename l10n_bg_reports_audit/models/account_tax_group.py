# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_bg_tax_tag_ids = fields.Many2many(
        comodel_name="account.account.tag",
        relation="account_tax_group_l10n_bg_tag_rel",
        column1="tax_group_id",
        column2="tag_id",
        string="BG tax tags",
        help=(
            "Additional tax tags to apply on tax lines when the tax group has "
            "payable/receivable accounts set."
        ),
    )
