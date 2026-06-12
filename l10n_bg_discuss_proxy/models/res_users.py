# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    # Маркер — Discuss съобщенията в каналите на този потребител се излъчват
    # към Centrifugo `discuss:<login>`, за да ги слуша външен Claude.
    claude_discuss_proxy = fields.Boolean(
        string="Listen to my Discuss via Claude proxy",
        help="Publish messages from channels I'm a member of to the Centrifugo "
             "proxy so an external Claude can listen and reply.")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["claude_discuss_proxy"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["claude_discuss_proxy"]
