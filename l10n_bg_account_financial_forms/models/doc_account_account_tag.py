#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class DocAccountAccountTag(models.Model):
    _inherit = "doc.account.account.tag"

    field_len = fields.Integer("Field len")
    field_type = fields.Selection(
        selection=[
            ("char", _("Character")),
            ("float", _("Float")),
            ("integer", _("Integer")),
        ],
        string="Field type",
    )
