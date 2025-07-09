#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, tools


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def init(self):
        super().init()
        tools.create_index(
            self._cr,
            'account_move_line_account_date_idx',  # Odoo конвенция за именуване
            'account_move_line',
            ['account_id', 'date']
        )
