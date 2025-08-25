from odoo import models, fields


class BankTransaction(models.Model):
    _name = 'bank.transaction'
    _description = 'Bank Transaction'

    transaction_id = fields.Char(string="Transaction ID", index=True)
    booking_date = fields.Date(string="Booking Date")
    value_date = fields.Date(string="Value Date")
    transaction_date = fields.Date(string="Transaction Date")
    amount = fields.Monetary(string="Amount")
    currency_id = fields.Many2one('res.currency', string="Currency")
    partner_name = fields.Char(string="Partner Name")
    ref = fields.Char(string="Reference")
    reference = fields.Char(string="Reference")
    description = fields.Text(string="Description")
    account_iban = fields.Char(string="Account IBAN")
    journal_id = fields.Many2one('account.journal', string="Journal")
    raw_data = fields.Json(string="Raw Data")
