# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class L10nBgTelegramPackage(models.Model):
    _name = "l10n.bg.telegram.package"
    _description = "Telegram Bot Package"
    _order = "sequence, id"

    bot_id = fields.Many2one("l10n.bg.telegram.bot", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(
        required=True, translate=True, help="Button text, e.g. 10 hours — €470."
    )
    product_id = fields.Many2one(
        "product.product", required=True, domain=[("sale_ok", "=", True)]
    )
    quantity = fields.Float(default=1.0, required=True, digits="Product Unit")
