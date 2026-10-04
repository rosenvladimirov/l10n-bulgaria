# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_open_page_translation(self):
        """Отваря съветника с вече заредените термини на страницата."""
        self.ensure_one()
        wizard = self.env["product.page.translate.wizard"].create(
            {"product_tmpl_id": self.id}
        )
        wizard._load_lines()
        return wizard._action_reopen()
