#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_bg_account_tag_ids = fields.Many2many(
        string="NSI Account Tags",
        comodel_name='account.account.tag',
        relation='l10n_bg_product_template_account_tag_rel',  # Нова уникална релационна таблица
        column1='product_template_id',
        column2='account_tag_id',
        domain="[('applicability', '=', 'l10n_bg_product')]",
        help="Bulgaria NSI report tags to be set on the base and tax journal items created for this product."
    )
