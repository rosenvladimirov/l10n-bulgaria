# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_open_page_translation(self):
        """Бутонът е на формата на шаблона, а формата на варианта я наследява.

        Без метода тук всяко разширение на формата на варианта пада при
        валидиране („not a valid action on product.product“) — страницата е
        на шаблона, затова се отваря неговата.
        """
        self.ensure_one()
        return self.product_tmpl_id.action_open_page_translation()
