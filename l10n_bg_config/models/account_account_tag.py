#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountAccountTag(models.Model):
    _inherit = "account.account.tag"

    description = fields.Text("Description", translate=True)
