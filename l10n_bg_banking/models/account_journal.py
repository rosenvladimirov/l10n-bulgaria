from odoo import models, tools, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.addons.base.models.res_bank import sanitize_account_number


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _import_bank_statement_custom(self):
        """Custom bank statement import method for InfoPay integration"""
        statement_ids_all = []
        notifications_all = {}

        # Let the appropriate implementation module parse the file and return the required data
        # The active_id is passed in context in case an implementation module requires information about the wizard state (see QIF)
        currency_code, account_number, stmts_vals = self._parse_bank_statement_from_transactions()
        # Check raw data
        self._check_parsed_data(stmts_vals, account_number)
        # Try to find the currency and journal in odoo
        journal = self._find_additional_data(currency_code, account_number)
        # If no journal found, ask the user about creating one
        if not journal.default_account_id:
            raise UserError(_('You have to set a Default Account for the journal: %s', journal.name))
        # Prepare statement data to be used for bank statements creation
        stmts_vals = self._complete_bank_statement_vals_custom(stmts_vals, journal, account_number)
        # Create the bank statements
        statement_ids, dummy, notifications = self._create_bank_statements(stmts_vals)
        statement_ids_all.extend(statement_ids)

        msg = ""
        for notif in notifications:
            msg += (
                f"{notif['message']}"
            )
        if notifications:
            notifications_all = msg

        statements = self.env['account.bank.statement'].browse(statement_ids_all)
        line_to_reconcile = statements.line_ids
        if line_to_reconcile:
            # 'limit_time_real_cron' defaults to -1.
            # Manual fallback applied for non-POSIX systems where this key is disabled (set to None).
            cron_limit_time = tools.config['limit_time_real_cron'] or -1
            limit_time = cron_limit_time if 0 < cron_limit_time < 180 else 180
            line_to_reconcile._cron_try_auto_reconcile_statement_lines(limit_time=limit_time)

        result = self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            extra_domain=[('statement_id', 'in', statements.ids)],
            default_context={
                'search_default_not_matched': True,
                'default_journal_id': statements[:1].journal_id.id,
                'notifications': notifications_all,
            },
        )

        return result

    def _complete_bank_statement_vals_custom(self, stmts_vals, journal, account_number):
        for st_vals in stmts_vals:
            if not st_vals.get('reference'):
                st_vals['reference'] = True
            for line_vals in st_vals['transactions']:
                line_vals['journal_id'] = journal.id
                unique_import_id = line_vals.get('unique_import_id')
                if unique_import_id:
                    sanitized_account_number = sanitize_account_number(account_number)
                    line_vals['unique_import_id'] = (
                                                            sanitized_account_number and sanitized_account_number + '-' or '') + str(
                        journal.id) + '-' + unique_import_id

                if not line_vals.get('partner_bank_id'):
                    # Find the partner and his bank account or create the bank account. The partner selected during the
                    # reconciliation process will be linked to the bank when the statement is closed.
                    identifying_string = line_vals.get('account_number')
                    if identifying_string:
                        if line_vals.get('partner_id'):
                            partner_bank = self.env['res.partner.bank'].search([
                                ('acc_number', '=', identifying_string),
                                ('partner_id', '=', line_vals['partner_id'])
                            ])
                        else:
                            partner_bank = self.env['res.partner.bank'].search([
                                ('acc_number', '=', identifying_string),
                                ('company_id', 'in', (False, journal.company_id.id))
                            ])
                        # If multiple partners share the same account number, do not try to guess and just avoid setting it
                        if partner_bank and len(partner_bank) == 1:
                            line_vals['partner_bank_id'] = partner_bank.id
                            line_vals['partner_id'] = partner_bank.partner_id.id
        return stmts_vals

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
