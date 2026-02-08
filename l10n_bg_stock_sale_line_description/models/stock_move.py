# Copyright 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    sale_line_description = fields.Text(
        related="sale_line_id.name",
        readonly=True,
        store=False,
    )
