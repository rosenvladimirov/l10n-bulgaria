#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("currency_id", "company_id", "move_id.date")
    def _compute_currency_rate(self):
        res = super()._compute_currency_rate()
        for line in self:
            if (line.move_id.l10n_bg_type_vat in ('in_customs', 'out_customs')
                    and self._context.get("statistic_rate")):
                line.currency_rate = line.move_id.l10n_bg_currency_rate
        return res

    @api.onchange("amount_currency", "currency_id", "currency_rate")
    def _inverse_amount_currency(self):
        res = super()._inverse_amount_currency()
        for line in self:
            if (
                line.currency_id != line.company_id.currency_id
                and line.move_id.l10n_bg_type_vat in ('in_customs', 'out_customs')
                and self._context.get("statistic_rate")
            ):
                line.balance = line.company_id.currency_id.round(
                    line.amount_currency / line.currency_rate
                )
        return res
