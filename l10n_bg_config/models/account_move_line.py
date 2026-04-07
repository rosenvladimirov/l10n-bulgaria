#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = ["account.move.line", "l10n.bg.config.mixin"]
    _name = "account.move.line"
