# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools, _
from odoo.addons.l10n_bg_tax_admin.models.product_category import l10n_bg_member_163a


class ProductProduct(models.Model):
    _inherit = "product.product"

    l10n_bg_art_163a = fields.Selection(selection=l10n_bg_member_163a, string='Art. 163a from VAT')
