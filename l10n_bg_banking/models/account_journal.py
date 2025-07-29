from setuptools.dist import sequence

from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def import_psd2_transactions(self, transaction_list):
        currency = self.env['res.currency']
        for journal in self:
            for tx in transaction_list:
                vals = {
                    'transaction_id': tx.get('transactionId'),
                    'booking_date': tx.get('bookingDate'),
                    'value_date': tx.get('valueDate'),
                    'amount': tx.get('transactionAmount', {}).get('amount'),
                    'currency_id': currency.search([('name', '=', tx.get('transactionAmount', {}).get('currency'))],
                                                   limit=1).id,
                    'partner_name': tx.get('creditorName') or tx.get('debtorName'),
                    'ref': tx.get('remittanceInformationUnstructured') or tx.get('transactionId'),
                    'account_iban': (
                        (tx.get('creditorAccount') or {}).get('iban') or
                        (tx.get('debtorAccount') or {}).get('iban')
                    ),
                    'journal_id': journal.id,
                    'raw_data': tx,
                }
                # Upsert
                existing = self.env['bank.transaction'].search([
                    ('transaction_id', '=', vals['transaction_id']),
                    ('journal_id', '=', journal.id)
                ], limit=1)
                if existing:
                    existing.write(vals)
                else:
                    self.env['bank.transaction'].create(vals)

    def _parse_bank_statement_file(self, attachment):
        if not "PSD2" in attachment.name:
            return super()._parse_bank_statement_file(attachment)

        transactions = self.env['bank.transaction'].search([
            ('account_iban', '=', self.bank_account_id.acc_number)
        ])

        if not transactions:
            return super()._parse_bank_statement_file(attachment)

        currency_code = transactions[0].currency_id.name
        account_number = transactions[0].account_iban

        grouped = {}
        sequence = 0
        for tx in transactions:
            key = (tx.account_iban, tx.booking_date)
            if key not in grouped:
                grouped[key] = {
                    'name': f'Statement {tx.booking_date}',
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
