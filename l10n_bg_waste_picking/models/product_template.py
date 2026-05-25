# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Флаг is_waste_product на продуктовия шаблон.

При truth-y стойност, всеки stock.move.line с този продукт изисква
waste_code_id при валидиране на picking.
"""
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_waste_product = fields.Boolean(
        string="Waste Product",
        help="When set, stock pickings containing this product require a "
             "waste code (l10n.bg.waste.code) on each move line at "
             "validation time. Quotas from active permits are enforced.",
    )
    default_waste_code_id = fields.Many2one(
        "l10n.bg.waste.code",
        string="Default Waste Code",
        domain="[('level','=','code')]",
        help="Suggested code prefilled in the validation wizard. Users can "
             "still override per move line.",
    )
