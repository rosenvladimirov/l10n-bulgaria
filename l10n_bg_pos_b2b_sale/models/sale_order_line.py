# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    l10n_bg_pos_line_uuid = fields.Char(
        string="Point of Sale Line",
        copy=False,
        index="btree_not_null",
        help="Line of the wholesale order in the Point of Sale this quotation "
        "line was saved from.",
    )
