from odoo import models, tools, _
from odoo.exceptions import UserError, RedirectWarning
import logging

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _import_bank_statement_custom(self, attachments):
        statement_ids_all = []
        notifications_all = {}
        errors = {}
        # Let the appropriate implementation module parse the file and return the required data
        # The active_id is passed in context in case an implementation module requires information about the wizard state (see QIF)
        for attachment in attachments:
            try:
                currency_code, account_number, stmts_vals = self._parse_bank_statement_file_custom(attachment)
                # Check raw data
                self._check_parsed_data(stmts_vals, account_number)
                # Try to find the currency and journal in odoo
                journal = self._find_additional_data(currency_code, account_number)
                # If no journal found, ask the user about creating one
                if not journal.default_account_id:
                    raise UserError(_('You have to set a Default Account for the journal: %s', journal.name))
                # Prepare statement data to be used for bank statements creation
                stmts_vals = self._complete_bank_statement_vals(stmts_vals, journal, account_number, attachment)
                # Create the bank statements
                statement_ids, dummy, notifications = self._create_bank_statements(stmts_vals)
                statement_ids_all.extend(statement_ids)

                # Now that the import worked out, set it as the bank_statements_source of the journal
                if journal.bank_statements_source != 'file_import':
                    # Use sudo() because only 'account.group_account_manager'
                    # has write access on 'account.journal', but 'account.group_account_user'
                    # must be able to import bank statement files
                    journal.sudo().bank_statements_source = 'file_import'

                msg = ""
                for notif in notifications:
                    msg += (
                        f"{notif['message']}"
                    )
                if notifications:
                    notifications_all[attachment.name] = msg
            except (UserError, RedirectWarning) as e:
                errors[attachment.name] = e.args[0]

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

        if errors:
            error_msg = _("The following files could not be imported:\n")
            error_msg += "\n".join([f"- {attachment_name}: {msg}" for attachment_name, msg in errors.items()])
            if statements:
                self.env.cr.commit()  # save the correctly uploaded statements to the db before raising the errors
                raise RedirectWarning(error_msg, result, _('View successfully imported statements'))
            else:
                raise UserError(error_msg)
        return result

    def _parse_bank_statement_file_custom(self, attachment):
        transactions = self.env['bank.transaction'].search([
            ('journal_id', '=', self.id)
        ], order='booking_date, value_date, transaction_id')

        if not transactions:
            raise UserError(_("No transactions found for the specified account."))

        currency_code = transactions[0].currency_id.name
        account_number = transactions[0].account_iban

        # Group transactions by date to create daily statements
        grouped = {}
        for tx in transactions:
            key = tx.booking_date
            if key not in grouped:
                # Get the first transaction of the day to determine opening balance
                day_transactions = [t for t in transactions if t.booking_date == key]
                day_transactions.sort(key=lambda x: (x.value_date, x.transaction_id))
                
                # Calculate opening balance for this day
                if day_transactions:
                    first_tx = day_transactions[0]
                    opening_balance = first_tx.balance_before_transaction
                else:
                    opening_balance = 0.0
                
                grouped[key] = {
                    'name': f'Statement {key}',
                    'date': key,
                    'opening_balance': opening_balance,
                    'closing_balance': 0.0,  # Will be calculated
                    'transactions': [],
                }
            
            # Add transaction to the day's group
            grouped[key]['transactions'].append({
                'sequence': len(grouped[key]['transactions']) + 1,
                'date': tx.booking_date,
                'amount': tx.amount,
                'payment_ref': tx.ref,
                'partner_name': tx.partner_name,
                'account_number': tx.account_iban,
                'unique_import_id': tx.transaction_id,
                'ref': tx.ref,
                'balance_after': tx.balance_after_transaction,
                'balance_before': tx.balance_before_transaction,
            })
            
            # Update closing balance for this day
            grouped[key]['closing_balance'] = tx.balance_after_transaction

        stmts_vals = list(grouped.values())
        return currency_code, account_number, stmts_vals

    def _complete_bank_statement_vals(self, stmts_vals, journal, account_number, attachment):
        """Complete bank statement values with balance information"""
        for stmt_vals in stmts_vals:
            # Ensure we have proper balance information
            if 'opening_balance' not in stmt_vals:
                stmt_vals['opening_balance'] = 0.0
            if 'closing_balance' not in stmt_vals:
                stmt_vals['closing_balance'] = 0.0
            
            # Calculate total amount from transactions
            total_amount = sum(tx.get('amount', 0.0) for tx in stmt_vals.get('transactions', []))
            
            # Verify balance consistency
            expected_closing = stmt_vals['opening_balance'] + total_amount
            if abs(expected_closing - stmt_vals['closing_balance']) > 0.01:  # Allow for small rounding differences
                # Log warning but continue - the API balance is considered authoritative
                _logger.warning(
                    f"Balance mismatch for statement {stmt_vals['name']}: "
                    f"expected {expected_closing}, got {stmt_vals['closing_balance']}"
                )
        
        return stmts_vals

    def _create_bank_statements(self, stmts_vals):
        """Create bank statements with balance information"""
        statements = self.env['account.bank.statement']
        notifications = []
        
        for stmt_vals in stmts_vals:
            # Create the bank statement
            statement_vals = {
                'name': stmt_vals['name'],
                'date': stmt_vals['date'],
                'journal_id': self.id,
                'balance_start': stmt_vals.get('opening_balance', 0.0),
                'balance_end_real': stmt_vals.get('closing_balance', 0.0),
            }
            
            statement = self.env['account.bank.statement'].create(statement_vals)
            statements |= statement
            
            # Create statement lines
            for line_vals in stmt_vals.get('transactions', []):
                line_vals['statement_id'] = statement.id
                line_vals['journal_id'] = self.id
                
                # Create the statement line
                statement_line = self.env['account.bank.statement.line'].create(line_vals)
                
                # Update the bank transaction with statement information
                if line_vals.get('unique_import_id'):
                    transaction = self.env['bank.transaction'].search([
                        ('transaction_id', '=', line_vals['unique_import_id']),
                        ('journal_id', '=', self.id)
                    ], limit=1)
                    if transaction:
                        transaction.write({
                            'statement_id': statement.id,
                            'statement_line_id': statement_line.id,
                        })
            
            # Add notification about balance
            if stmt_vals.get('opening_balance') is not None and stmt_vals.get('closing_balance') is not None:
                notifications.append({
                    'message': f"Statement {stmt_vals['name']}: Opening balance {stmt_vals['opening_balance']:.2f}, Closing balance {stmt_vals['closing_balance']:.2f}"
                })
        
        return statements.ids, False, notifications

    def _find_additional_data(self, currency_code, account_number):
        """Find the journal based on currency and account number"""
        # For our implementation, we return self since we're already working with a specific journal
        return self

    def _check_parsed_data(self, stmts_vals, account_number):
        """Check if the parsed data is valid"""
        if not stmts_vals:
            raise UserError(_("No valid statements found in the parsed data."))
        
        for stmt_vals in stmts_vals:
            if not stmt_vals.get('transactions'):
                raise UserError(_("Statement {} has no transactions.".format(stmt_vals.get('name', 'Unknown'))))

    def action_verify_statement_balances(self):
        """Verify that statement balances are consistent with transaction amounts"""
        statements = self.env['account.bank.statement'].search([
            ('journal_id', '=', self.id),
            ('state', '!=', 'cancelled')
        ])
        
        verification_results = []
        
        for statement in statements:
            # Calculate expected closing balance
            total_amount = sum(line.amount for line in statement.line_ids)
            expected_closing = statement.balance_start + total_amount
            actual_closing = statement.balance_end_real
            
            # Check for balance discrepancies
            balance_diff = abs(expected_closing - actual_closing)
            is_balanced = balance_diff < 0.01  # Allow for small rounding differences
            
            verification_results.append({
                'statement': statement.name,
                'date': statement.date,
                'opening_balance': statement.balance_start,
                'total_transactions': total_amount,
                'expected_closing': expected_closing,
                'actual_closing': actual_closing,
                'difference': balance_diff,
                'is_balanced': is_balanced,
            })
        
        # Return verification results
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Balance Verification Results',
                'message': self._format_verification_results(verification_results),
                'type': 'info',
            }
        }
    
    def _format_verification_results(self, results):
        """Format verification results for display"""
        if not results:
            return "No statements found for verification."
        
        message = "Balance verification results:\n\n"
        
        for result in results:
            status = "✓ BALANCED" if result['is_balanced'] else "✗ UNBALANCED"
            message += f"{result['statement']} ({result['date']}): {status}\n"
            message += f"  Opening: {result['opening_balance']:.2f}\n"
            message += f"  Transactions: {result['total_transactions']:.2f}\n"
            message += f"  Expected closing: {result['expected_closing']:.2f}\n"
            message += f"  Actual closing: {result['actual_closing']:.2f}\n"
            
            if not result['is_balanced']:
                message += f"  Difference: {result['difference']:.2f}\n"
            message += "\n"
        
        return message

    def action_get_current_balance(self):
        """Get current account balance from Infopay API for comparison"""
        try:
            # Get the bank account from this journal
            bank_account = self.bank_account_id
            if not bank_account:
                raise UserError(_("No bank account configured for this journal."))
            
            # Get the bank record
            bank = bank_account.bank_id
            if not bank:
                raise UserError(_("No bank configured for this account."))
            
            # Check if Infopay is configured
            if not bank.infopay_client_id or not bank.infopay_access_token:
                raise UserError(_("Infopay is not configured for this bank."))
            
            # Get the IBAN
            iban = bank_account.acc_number
            if not iban:
                raise UserError(_("No IBAN configured for this account."))
            
            # Get accounts from Infopay to find the account ID
            if not bank._is_session_valid():
                bank._create_infopay_session()
            
            accounts_response = bank._get_accounts_list()
            if not accounts_response:
                raise UserError(_("Failed to fetch accounts from Infopay API."))
            
            accounts = accounts_response.get('Accounts', [])
            account_id = None
            
            for account in accounts:
                if account.get('IBAN', '') == iban:
                    account_id = account.get('AccountId')
                    break
            
            if not account_id:
                raise UserError(_("Account with IBAN {} not found in Infopay.").format(iban))
            
            # Get current balance
            balance_response = bank._get_account_balance(account_id)
            if not balance_response:
                raise UserError(_("Failed to fetch balance from Infopay API."))
            
            balance_info = balance_response.get('Balance', {})
            current_balance = balance_info.get('amount', 0.0)
            currency = balance_info.get('currency', 'BGN')
            
            # Compare with latest statement closing balance
            latest_statement = self.env['account.bank.statement'].search([
                ('journal_id', '=', self.id),
                ('state', '!=', 'cancelled')
            ], order='date desc', limit=1)
            
            comparison_message = f"Current balance from Infopay: {current_balance:.2f} {currency}\n\n"
            
            if latest_statement:
                statement_balance = latest_statement.balance_end_real
                difference = abs(current_balance - statement_balance)
                comparison_message += f"Latest statement closing balance: {statement_balance:.2f}\n"
                comparison_message += f"Difference: {difference:.2f}\n"
                
                if difference < 0.01:
                    comparison_message += "✓ Balances match (within rounding tolerance)"
                else:
                    comparison_message += "⚠ Balance discrepancy detected"
            else:
                comparison_message += "No statements found for comparison."
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Current Balance from Infopay',
                    'message': comparison_message,
                    'type': 'info',
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error Getting Balance',
                    'message': str(e),
                    'type': 'danger',
                }
            }

    def action_handle_balance_verification(self):
        """Handle balance verification based on context action"""
        action = self.env.context.get('default_action')
        
        if action == 'verify_balances':
            return self.action_verify_statement_balances()
        elif action == 'get_balance':
            return self.action_get_current_balance()
        else:
            # Default action - show a form to select the journal
            return {
                'type': 'ir.actions.act_window',
                'name': 'Select Journal for Balance Verification',
                'res_model': 'account.journal',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_type': 'bank'},
            }
