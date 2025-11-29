# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, Command, _, fields
from odoo.tools import get_lang, SQL


class GenericTaxReportCustomHandler(models.AbstractModel):
    _inherit = 'account.generic.tax.report.handler'

    def _get_add_line_tax_group_closing_items(self, name, advance_balance, account, tag_ids=False):
        return {
            'name': name,
            'debit': abs(advance_balance) if advance_balance < 0 else 0,
            'credit': abs(advance_balance) if advance_balance > 0 else 0,
            'account_id': account,
            'tax_tag_ids': tag_ids and [Command.set(tag_ids)] or False,
        }

    def _get_add_tax_group_closing_items(self, key, total):
        return {
            'name': _('Payable tax amount') if total < 0 else _('Receivable tax amount'),
            'debit': total if total > 0 else 0,
            'credit': abs(total) if total < 0 else 0,
            'account_id': key[2] if total < 0 else key[1],
            'tax_tag_ids': key[3] and [Command.set(key[3])] or False,
        }
