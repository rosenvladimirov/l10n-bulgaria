from odoo import models, tools, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.addons.base.models.res_bank import sanitize_account_number


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _import_bank_statement_infopay(self):
        """Custom bank statement import method for InfoPay integration"""
        pass

    def _parse_bank_statement_from_transactions(self):
        """Parse bank statement from InfoPay transactions"""
        transactions = self.env['bank.transaction'].search([
            ('journal_id', '=', self.id)
        ])

        if not transactions:
            raise UserError(_("No transactions found for the specified account."))

        currency_code = transactions[0].currency_id.name
        account_number = transactions[0].account_iban

        grouped = {}
        sequence = 0
        for tx in transactions:
            key = (tx.account_iban, tx.booking_date)
            if key not in grouped:
                grouped[key] = {
                    'name': 'Statement {}'.format(tx.booking_date),
                    'date': tx.booking_date,
                    'transactions': [],
                }
            sequence += 1
            grouped[key]['transactions'].append({
                'sequence': sequence,
                'date': tx.booking_date,
                'amount': tx.amount,
                'payment_ref': tx.ref,
                'partner_name': tx.partner_name,
                'account_number': tx.account_iban,
                'unique_import_id': tx.transaction_id,
                'ref': tx.ref,
            })

        stmts_vals = list(grouped.values())
        return currency_code, account_number, stmts_vals
