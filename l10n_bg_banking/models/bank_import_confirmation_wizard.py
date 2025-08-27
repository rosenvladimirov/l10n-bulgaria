import datetime
import logging

from odoo import fields, models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Check if requests module is available
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    _logger.warning("Python 'requests' module not available. InfoPay integration will not work.")


def clean_dict_for_json(d):
    if isinstance(d, dict):
        return {k: clean_dict_for_json(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [clean_dict_for_json(i) for i in d]
    elif isinstance(d, (datetime.date, datetime.datetime)):
        return d.isoformat()
    else:
        return d


def get_configured_journals(env):
    """Get all bank journals that have bank accounts with IBAN configured"""
    return env['account.journal'].search([
        ('type', '=', 'bank'),
        ('bank_account_id', '!=', False),
        ('bank_account_id.acc_number', '!=', False)
    ])


class BankImportConfirmationWizard(models.TransientModel):
    _name = 'bank.import.confirmation.wizard'
    _description = 'InfoPay Import Wizard'

    # Configuration reference
    config_id = fields.Many2one('res.config.settings', string='Configuration', required=True)

    # Status fields
    status = fields.Selection([
        ('draft', 'Draft'),
        ('validating', 'Validating Configuration'),
        ('connecting', 'Connecting to InfoPay'),
        ('importing', 'Importing Transactions'),
        ('completed', 'Completed'),
        ('error', 'Error')
    ], string="Status", default='draft', readonly=True)

    status_message = fields.Text(string="Status Message", readonly=True)

    # Import results
    transactions_imported = fields.Integer(string="Transactions Imported", default=0, readonly=True)
    journals_processed = fields.Integer(string="Journals Processed", default=0, readonly=True)

    def action_confirm_import(self):
        """Start the InfoPay import process"""
        if not REQUESTS_AVAILABLE:
            raise UserError("Python 'requests' module is not available. Please install it with: pip install requests")

        # Validate configuration
        self._validate_configuration()

        # Start import process
        self.write({'status': 'validating'})

        self.write({
            'status': 'connecting',
            'status_message': f"Connecting to InfoPay..."
        })
        # Create InfoPay session
        session_data = self._create_infopay_session()
        if not session_data:
            raise UserError("Failed to create InfoPay session. Please check your credentials.")

        try:
            configured_journals = get_configured_journals(self.env)
            if not configured_journals:
                raise UserError("No journals are configured for InfoPay import. Please configure at least one journal.")

            self.write({
                'status': 'importing',
                'status_message': "Session created successfully. Importing transactions..."
            })

            # Import transactions for each journal
            accounts = self._get_accounts_list(session_data)

            # Refresh balances and transactions
            self.refresh_balances_and_transactions(session_data, accounts)

            # Wait a bit for the transactions to be available
            total_transactions = 0
            journals = []
            for account in accounts:
                iban = account.get('IBAN')
                journal = next((j for j in configured_journals if
                                j.bank_account_id and j.bank_account_id.acc_number.replace(' ', '') == iban), False)
                if not journal:
                    continue

                journals.append(journal)

                booked_transactions = self._get_transactions(session_data, account)
                for tx in booked_transactions:
                    transaction_amount = tx.get('TransactionAmount', {})

                    vals = {
                        'transaction_id': tx.get('TransactionId'),
                        'booking_date': tx.get('BookingDate'),
                        'value_date': tx.get('ValueDate'),
                        'amount': transaction_amount.get('amount'),
                        'currency_id': self.env['res.currency'].search(
                            [('name', '=', transaction_amount.get('currency', 'BGN'))],
                            limit=1).id,
                        'partner_name': tx.get('CreditorName') or tx.get('DebtorName'),
                        'ref': tx.get('RemittanceInformationUnstructured') or tx.get('TransactionId'),
                        'account_iban': iban,
                        'journal_id': journal.id,
                        'raw_data': tx,
                    }

                    existing = self.env['bank.transaction'].search([
                        ('transaction_id', '=', vals['transaction_id']),
                        ('journal_id', '=', journal.id)
                    ], limit=1)

                    if existing:
                        existing.write(clean_dict_for_json(vals))
                    else:
                        self.env['bank.transaction'].create(clean_dict_for_json(vals))

                total_transactions += len(booked_transactions)

            for journal in journals:
                journal._import_bank_statement_infopay()

            self.write({
                'status': 'completed',
                'status_message': f"Import completed successfully! {total_transactions} transactions imported from {len(journals)} journal(s).",
                'transactions_imported': total_transactions,
                'journals_processed': len(journals)
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Import Completed',
                    'message': f'Successfully imported {total_transactions} transactions from {len(journals)} journal(s).',
                    'type': 'success',
                    'sticky': True,
                }
            }

        except Exception as e:
            self.write({
                'status': 'error',
                'status_message': f"Import failed: {str(e)}"
            })
            raise UserError(f"Import failed: {str(e)}")
        finally:
            # Cleanup session
            self._cleanup_infopay_session(session_data)

    def _validate_configuration(self):
        """Validate that InfoPay configuration is complete"""
        if not self.config_id.infopay_api_url:
            raise UserError("InfoPay API URL is not configured.")

        if not self.config_id.infopay_client_id:
            raise UserError("InfoPay Client ID is not configured.")

        if not self.config_id.infopay_access_token:
            raise UserError("InfoPay Access Token is not configured.")

    def _create_infopay_session(self):
        """Create a new session with Infopay API"""
        url = "{}/api/session".format(self.config_id.infopay_api_url)

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "curl/7.68.0"
        }

        data = {
            "uniqueId": self.config_id.infopay_client_id,
            "accessToken": self.config_id.infopay_access_token
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            session_data = response.json()
            session_id = session_data.get("SessionId")
            session_key = session_data.get("SessionKey")

            if not session_id or not session_key:
                raise UserError("Failed to create session with Infopay API.")

            return {
                'sessionId': session_id,
                'sessionKey': session_key
            }
        except requests.exceptions.RequestException as e:
            print("=== ERROR DETAILS ===")
            print("Error type: {}".format(type(e)))
            print("Error message: {}".format(str(e)))
            if hasattr(e, 'response'):
                print("Response status: {}".format(e.response.status_code))
                print("Response text: {}".format(e.response.text))
            raise UserError("Failed to create session with Infopay API: {}".format(e))

    def _cleanup_infopay_session(self, session_data):
        """Clean up InfoPay API session"""
        try:
            url = f"{self.config_id.infopay_api_url}/api/session/cleanup"
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "curl/7.68.0",
                'sessionId': session_data['sessionId'],
                'sessionKey': session_data['sessionKey']
            }

            requests.post(url, headers=headers, timeout=10)
        except Exception as e:
            _logger.warning(f"Failed to cleanup InfoPay session: {e}")

    def _get_accounts_list(self, session_data):
        """Get list of accounts from InfoPay"""
        url = f"{self.config_id.infopay_api_url}/api/accounts"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "curl/7.68.0",
            'sessionId': session_data['sessionId'],
            'sessionKey': session_data['sessionKey']
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        accounts = data.get('Accounts', [])
        return accounts

    def _get_transactions(self, session_data, account):
        """Get transactions for a specific account and period"""
        url = f"{self.config_id.infopay_api_url}/api/accounts/{account.get('AccountId')}/transactions"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "curl/7.68.0",
            'sessionId': session_data['sessionId'],
            'sessionKey': session_data['sessionKey']
        }

        # Use very old start date (1900-01-01) and current date for end date
        beginning_of_current_month = datetime.date.today().replace(day=1)
        end_date = datetime.date.today()
        start_date = (beginning_of_current_month - datetime.timedelta(days=1)).replace(day=1)

        params = {
            'dateFrom': start_date.strftime('%Y-%m-%d'),
            'dateTo': end_date.strftime('%Y-%m-%d')
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        trs = data.get('Transactions')
        if not trs:
            return []
        return trs.get('Booked', [])

    def action_cancel(self):
        """Cancel the import operation"""
        return {'type': 'ir.actions.act_window_close'}

    def action_retry(self):
        """Retry the import operation"""
        self.write({'status': 'draft', 'status_message': ''})
        return self.action_confirm_import()

    def refresh_balances_and_transactions(self, session_data, accounts):
        url = f"{self.config_id.infopay_api_url}/api/synchronizations/balancesAndTransactions/refresh"

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "curl/7.68.0",
            'sessionId': session_data['sessionId'],
            'sessionKey': session_data['sessionKey']
        }

        account_ids = [acc.get('AccountId') for acc in accounts if acc.get('AccountId')]

        data = {
            "AccountIds": account_ids
        }

        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

