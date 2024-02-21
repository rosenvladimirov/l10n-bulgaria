# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.addons.l10n_bg_tax_admin.models.product_category import l10n_bg_member_163a

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_bg_art_163a = fields.Selection(selection=l10n_bg_member_163a,
                                        compute='_compute_l10n_bg_art_163a',
                                        inverse='_inverse_l10n_bg_art_163a',
                                        string='Art 163a',
                                        store=True,
                                        precompute=True,
                                        )

    def _compute_l10n_bg_art_163a(self):
        for record in self:
            record.l10n_bg_art_163a = record.product_variant_id.l10n_bg_art_163a
            if not record.l10n_bg_art_163a:
                category_id = record.categ_id
                while True:
                    if category_id and category_id.l10n_bg_art_163a:
                        record.l10n_bg_art_163a = category_id.l10n_bg_art_163a
                    if category_id and category_id.parent_id:
                        category_id = category_id.parent_id
                    else:
                        break

    def _inverse_l10n_bg_art_163a(self):
        for record in self:
            for product_id in record.product_variant_ids:
                product_id.l10n_bg_art_163a = record.l10n_bg_art_163a
