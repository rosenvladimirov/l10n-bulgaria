# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Конфигурация за счетоводство на труд
    labor_accounting_enabled = fields.Boolean(
        string='Enable Labor Accounting',
        default=True,
        help='Ако е активирано, системата автоматично ще създава '
             'счетоводни записи за разходи за труд'
    )

    labor_expense_account_id = fields.Many2one(
        'account.account',
        string='Labor Expense Account',
        domain="[('account_type', '=', 'expense'), ('company_id', '=', id)]",
        help='Сметка за разходи за труд (например: 602 - Labor Costs)'
    )

    wip_account_id = fields.Many2one(
        'account.account',
        string='WIP Account',
        domain="[('account_type', '=', 'asset_current'), ('company_id', '=', id)]",
        help='Work in Progress сметка (например: 331 - WIP)'
    )

    manufacturing_journal_id = fields.Many2one(
        'account.journal',
        string='Manufacturing Journal',
        domain="[('type', '=', 'general'), ('company_id', '=', id)]",
        help='Дневник за производствени операции'
    )
