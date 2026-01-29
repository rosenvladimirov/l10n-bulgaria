#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends(
        "tax_ids",
        "tax_line_id",
        "tax_line_id.tax_group_id",
        "tax_line_id.tax_group_id.l10n_bg_tax_tag_ids",
    )
    def _compute_tax_tag_ids(self):
        super()._compute_tax_tag_ids()
        for line in self:
            tax_line = line.tax_line_id
            if not tax_line:
                continue
            tax_group = tax_line.tax_group_id
            if not tax_group or not tax_group.l10n_bg_tax_tag_ids:
                continue
            is_receivable = (
                tax_group.tax_receivable_account_id
                and line.account_id == tax_group.tax_receivable_account_id
                and line.balance > 0
            )
            is_payable = (
                tax_group.tax_payable_account_id
                and line.account_id == tax_group.tax_payable_account_id
                and line.balance < 0
            )
            if is_receivable or is_payable:
                line.tax_tag_ids = line.tax_tag_ids | tax_group.l10n_bg_tax_tag_ids

    def init(self):
        super().init()
        tools.create_index(
            self._cr,
            'account_move_line_account_date_idx',
            'account_move_line',
            ['account_id', 'date']
        )
