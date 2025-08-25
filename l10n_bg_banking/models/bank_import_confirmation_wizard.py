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


class BankImportConfirmationWizard(models.TransientModel):
    _name = 'bank.import.confirmation.wizard'
    _description = 'InfoPay Import Wizard'

    # Configuration reference
    config_id = fields.Many2one('res.config.settings', string='Configuration', required=True)

    # Period configuration
    integration_month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
        ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string="Integration Month", required=True)

    integration_year = fields.Integer(string="Integration Year", required=True)

    # Computed fields
    period_display = fields.Char(string="Period", compute='_compute_period_display', store=False)
    start_date = fields.Date(string="Start Date", compute='_compute_dates', store=False)
    end_date = fields.Date(string="End Date", compute='_compute_dates', store=False)

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

    @api.depends('integration_month', 'integration_year')
    def _compute_period_display(self):
        """Compute human-readable period description"""
        for record in self:
            if record.integration_month and record.integration_year:
                month_name = dict(self._fields['integration_month'].selection).get(record.integration_month)
                record.period_display = f"{month_name} {record.integration_year}"
            else:
                record.period_display = "Not set"

    @api.depends('integration_month', 'integration_year')
    def _compute_dates(self):
        """Compute start and end dates based on selected month and year"""
        for record in self:
            if record.integration_month and record.integration_year:
                # Create start date (first day of selected month and year)
                start_date = datetime.date(record.integration_year, int(record.integration_month), 1)

                # Create end date (last day of selected month and year)
                if int(record.integration_month) == 12:
                    # December - last day is December 31st
                    end_date = datetime.date(record.integration_year, 12, 31)
                else:
                    # For other months, get the first day of next month and subtract 1 day
                    next_month = int(record.integration_month) + 1
                    next_month_first = datetime.date(record.integration_year, next_month, 1)
                    end_date = next_month_first - datetime.timedelta(days=1)

                record.start_date = start_date
                record.end_date = end_date
            else:
                record.start_date = False
                record.end_date = False

    @api.model
    def create(self, vals):
        """Set default values from configuration"""
        if 'config_id' in vals:
            config = self.env['res.config.settings'].browse(vals['config_id'])
            if not vals.get('integration_month'):
                vals['integration_month'] = config.integration_month
            if not vals.get('integration_year'):
                vals['integration_year'] = config.integration_year
        return super().create(vals)

    def action_confirm_import(self):
        """Start the InfoPay import process"""
        if not REQUESTS_AVAILABLE:
            raise UserError("Python 'requests' module is not available. Please install it with: pip install requests")

        # Validate configuration
        self._validate_configuration()

        # Start import process
        self.write({'status': 'validating'})

        try:
            # Check for configured journals
            journals = self._get_configured_journals()
            if not journals:
                raise UserError("No bank journals with IBAN configured found. Please configure bank journals first.")

            self.write({
                'status': 'connecting',
                'status_message': f"Found {len(journals)} configured journal(s). Connecting to InfoPay..."
            })

            # Create InfoPay session
            session_data = self._create_infopay_session()
            if not session_data:
                raise UserError("Failed to create InfoPay session. Please check your credentials.")

            self.write({
                'status': 'importing',
                'status_message': "Session created successfully. Importing transactions..."
            })

            # Import transactions for each journal
            total_transactions = 0
            for journal in journals:
                transactions = self._import_transactions_for_journal(journal, session_data)
                total_transactions += len(transactions)

            # Cleanup session
            self._cleanup_infopay_session(session_data)

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

    def _validate_configuration(self):
        """Validate that InfoPay configuration is complete"""
        if not self.config_id.infopay_api_url:
            raise UserError("InfoPay API URL is not configured.")

        if not self.config_id.infopay_client_id:
            raise UserError("InfoPay Client ID is not configured.")

        if not self.config_id.infopay_access_token:
            raise UserError("InfoPay Access Token is not configured.")

        if not self.integration_month or not self.integration_year:
            raise UserError("Integration period is not set.")

    def _get_configured_journals(self):
        """Get all bank journals that have bank accounts with IBAN configured"""
        return self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('bank_account_id', '!=', False),
            ('bank_account_id.acc_number', '!=', False)
        ])

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
                'Content-Type': 'application/json',
                'sessionId': session_data['sessionId'],
                'sessionKey': session_data['sessionKey']
            }

            requests.post(url, headers=headers, timeout=10)
        except Exception as e:
            _logger.warning(f"Failed to cleanup InfoPay session: {e}")

    def _import_transactions_for_journal(self, journal, session_data):
        """Import transactions for a specific journal"""
        try:
            # Get account list for this journal's IBAN
            accounts = self._get_accounts_list(session_data, journal.bank_account_id.acc_number)

            transactions = []
            for account in accounts:
                account_transactions = self._get_transactions(session_data, account, journal)
                transactions.extend(account_transactions)

            # Create bank transactions
            created_transactions = []
            for trans_data in transactions:
                transaction = self.env['bank.transaction'].create({
                    'journal_id': journal.id,
                    'transaction_date': trans_data.get('date'),
                    'amount': trans_data.get('amount', 0.0),
                    'description': trans_data.get('description', ''),
                    'reference': trans_data.get('reference', ''),
                    'currency_id': journal.currency_id.id or journal.company_id.currency_id.id,
                })
                created_transactions.append(transaction)

            return created_transactions

        except Exception as e:
            _logger.error(f"Failed to import transactions for journal {journal.name}: {e}")
            raise UserError(f"Failed to import transactions for journal {journal.name}: {e}")

    def _get_accounts_list(self, session_data, iban):
        """Get list of accounts from InfoPay"""
        try:
            url = f"{self.config_id.infopay_api_url}/api/accounts/list"
            headers = {
                'Content-Type': 'application/json',
                'sessionId': session_data['sessionId'],
                'sessionKey': session_data['sessionKey']
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            if data.get('success'):
                # Filter accounts by IBAN if provided
                accounts = data.get('accounts', [])
                if iban:
                    accounts = [acc for acc in accounts if acc.get('iban') == iban]
                return accounts
            else:
                _logger.error(f"Failed to get accounts list: {data}")
                return []

        except requests.exceptions.RequestException as e:
            _logger.error(f"Failed to get accounts list: {e}")
            return []

    def _get_transactions(self, session_data, account, journal):
        """Get transactions for a specific account and period"""
        try:
            url = f"{self.config_id.infopay_api_url}/api/transactions"
            headers = {
                'Content-Type': 'application/json',
                'sessionId': session_data['sessionId'],
                'sessionKey': session_data['sessionKey']
            }

            params = {
                'accountId': account.get('id'),
                'startDate': self.start_date.strftime('%Y-%m-%d'),
                'endDate': self.end_date.strftime('%Y-%m-%d')
            }

            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            if data.get('success'):
                return data.get('transactions', [])
            else:
                _logger.error(f"Failed to get transactions: {data}")
                return []

        except requests.exceptions.RequestException as e:
            _logger.error(f"Failed to get transactions: {e}")
            return []

    def action_cancel(self):
        """Cancel the import operation"""
        return {'type': 'ir.actions.act_window_close'}

    def action_retry(self):
        """Retry the import operation"""
        self.write({'status': 'draft', 'status_message': ''})
        return self.action_confirm_import()
