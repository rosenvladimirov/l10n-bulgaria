#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    origin_transport_id = fields.Many2one(
        "res.country",
        string="Transport Country of origin",
        help="Transport Country of Origin",
    )
