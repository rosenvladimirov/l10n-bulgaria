from odoo import models, fields


class BankTransaction(models.Model):
    _name = 'bank.transaction'
    _description = 'Bank Transaction'

    transaction_id = fields.Char(string="Transaction ID", index=True)
    booking_date = fields.Date(string="Booking Date")
    value_date = fields.Date(string="Value Date")
    amount = fields.Monetary(string="Amount")
    currency_id = fields.Many2one('res.currency', string="Currency")
    partner_name = fields.Char(string="Partner Name")
    ref = fields.Char(string="Reference")
    account_iban = fields.Char(string="Account IBAN")
    journal_id = fields.Many2one('account.journal', string="Journal")
    raw_data = fields.Json(string="Raw Data")
    
    # Balance-related fields
    balance_after_transaction = fields.Monetary(string="Balance After Transaction", help="Account balance after this transaction")
    balance_before_transaction = fields.Monetary(string="Balance Before Transaction", help="Account balance before this transaction")
    running_balance = fields.Monetary(string="Running Balance", help="Calculated running balance")
    
    # Statement-related fields
    statement_id = fields.Many2one('account.bank.statement', string="Bank Statement")
    statement_line_id = fields.Many2one('account.bank.statement.line', string="Statement Line")
