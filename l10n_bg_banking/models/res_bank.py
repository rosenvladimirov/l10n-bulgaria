import datetime
import json
import random
import time

import requests

from odoo import fields, models, api
from odoo.exceptions import UserError


def clean_dict_for_json(d):
    if isinstance(d, dict):
        return {k: clean_dict_for_json(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [clean_dict_for_json(i) for i in d]
    elif isinstance(d, (datetime.date, datetime.datetime)):
        return d.isoformat()
    else:
        return d


class TransientAttachment(models.TransientModel):
    _name = 'transient.attachment'
    _description = 'Transient Attachment'

    name = fields.Char(string="Name", required=True)
    raw = fields.Boolean(string="Raw Data", required=True, default=False)


class ResBank(models.Model):
    _inherit = 'res.bank'

    # Infopay API Configuration
    infopay_api_url = fields.Char(string="Infopay API URL", default="https://integration.infopay.bg")
    infopay_client_id = fields.Char(string="Infopay Client ID")
    infopay_access_token = fields.Char(string="Infopay Access Token", store=True)

    # Session management
    infopay_session_id = fields.Char(string="Infopay Session ID", store=True)
    infopay_session_key = fields.Char(string="Infopay Session ID", store=True)

    # Month selection for integration
    integration_month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')
    ], string="Integration Month", default=lambda self: str(datetime.date.today().month).zfill(2),
       help="Select month for transaction import from Infopay")

    # Year selection for integration
    integration_year = fields.Integer(string="Integration Year",
                                    default=lambda self: datetime.date.today().year,
                                    help="Select year for transaction import from Infopay")

    # Integration date range configuration (computed from month and year)
    integration_start_date = fields.Date(string="Integration Start Date",
                                       compute='_compute_integration_dates',
                                       store=True,
                                       help="Start date for transaction import from Infopay (first day of selected month)")
    integration_end_date = fields.Date(string="Integration End Date",
                                     compute='_compute_integration_dates',
                                     store=True,
                                     help="End date for transaction import from Infopay (last day of selected month)")

    # Human-readable period description
    integration_period_display = fields.Char(string="Integration Period",
                                           compute='_compute_period_display',
                                           store=False,
                                           help="Human-readable description of the selected integration period")

    # Integration period status
    integration_period_status = fields.Selection([
        ('not_set', 'Not Set'),
        ('current', 'Current Month'),
        ('past', 'Past Month'),
        ('future', 'Future Month (Invalid)')
    ], string="Period Status", compute='_compute_period_status', store=False)

    # Compact period summary
    integration_period_summary = fields.Char(string="Period Summary",
                                           compute='_compute_period_summary',
                                           store=False,
                                           help="Compact summary of the integration period")

    @api.depends('integration_month', 'integration_year')
    def _compute_integration_dates(self):
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

                record.integration_start_date = start_date
                record.integration_end_date = end_date
            else:
                record.integration_start_date = False
                record.integration_end_date = False

    @api.depends('integration_month', 'integration_year')
    def _compute_period_display(self):
        """Compute human-readable period description"""
        for record in self:
            if record.integration_month and record.integration_year:
                month_name = dict(self._fields['integration_month'].selection).get(record.integration_month)
                record.integration_period_display = f"{month_name} {record.integration_year}"
            else:
                record.integration_period_display = "Not set"

    @api.depends('integration_month', 'integration_year')
    def _compute_period_status(self):
        """Compute the status of the selected integration period"""
        for record in self:
            if not record.integration_month or not record.integration_year:
                record.integration_period_status = 'not_set'
                continue

            today = datetime.date.today()
            selected_date = datetime.date(record.integration_year, int(record.integration_month), 1)

            if selected_date > today:
                record.integration_period_status = 'future'
            elif selected_date.year == today.year and selected_date.month == today.month:
                record.integration_period_status = 'current'
            else:
                record.integration_period_status = 'past'

    @api.depends('integration_month', 'integration_year', 'integration_start_date', 'integration_end_date')
    def _compute_period_summary(self):
        """Compute a compact summary of the integration period"""
        for record in self:
            if record.integration_month and record.integration_year and record.integration_start_date and record.integration_end_date:
                month_name = dict(self._fields['integration_month'].selection).get(record.integration_month)
                start_str = record.integration_start_date.strftime('%d/%m/%Y')
                end_str = record.integration_end_date.strftime('%d/%m/%Y')
                record.integration_period_summary = f"{month_name} {record.integration_year} ({start_str} - {end_str})"
            else:
                record.integration_period_summary = "Not configured"

    @api.constrains('integration_year')
    def _check_integration_year(self):
        """Validate that the integration year is reasonable"""
        for record in self:
            if record.integration_year:
                current_year = datetime.date.today().year
                if record.integration_year < 2000 or record.integration_year > current_year + 1:
                    raise UserError("Integration year must be between 2000 and {}.".format(current_year + 1))

    @api.constrains('integration_month', 'integration_year')
    def _check_integration_period(self):
        """Validate that the selected period is not in the future"""
        for record in self:
            if record.integration_month and record.integration_year:
                today = datetime.date.today()
                selected_date = datetime.date(record.integration_year, int(record.integration_month), 1)

                if selected_date > today:
                    raise UserError("Cannot select a period in the future. Please select a past or current month.")

    def action_set_current_month(self):
        """Set the current month and year for integration"""
        today = datetime.date.today()
        self.write({
            'integration_month': str(today.month).zfill(2),
            'integration_year': today.year,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Month Updated',
                'message': 'Set to current month: {} {}'.format(
                    dict(self._fields['integration_month'].selection).get(str(today.month).zfill(2)),
                    today.year
                ),
                'type': 'success',
            }
        }

    def action_previous_month(self):
        """Navigate to the previous month"""
        if not self.integration_month or not self.integration_year:
            return self.action_set_current_month()

        current_month = int(self.integration_month)
        current_year = self.integration_year

        if current_month == 1:
            # January -> December of previous year
            new_month = '12'
            new_year = current_year - 1
        else:
            # Previous month of same year
            new_month = str(current_month - 1).zfill(2)
            new_year = current_year

        self.write({
            'integration_month': new_month,
            'integration_year': new_year,
        })

        month_name = dict(self._fields['integration_month'].selection).get(new_month)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Month Updated',
                'message': 'Moved to: {} {}'.format(month_name, new_year),
                'type': 'success',
            }
        }

    def action_next_month(self):
        """Navigate to the next month"""
        if not self.integration_month or not self.integration_year:
            return self.action_set_current_month()

        current_month = int(self.integration_month)
        current_year = self.integration_year

        if current_month == 12:
            # December -> January of next year
            new_month = '01'
            new_year = current_year + 1
        else:
            # Next month of same year
            new_month = str(current_month + 1).zfill(2)
            new_year = current_year

        self.write({
            'integration_month': new_month,
            'integration_year': new_year,
        })

        month_name = dict(self._fields['integration_month'].selection).get(new_month)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Month Updated',
                'message': 'Moved to: {} {}'.format(month_name, new_year),
                'type': 'success',
            }
        }

    def action_reset_to_current_period(self):
        """Reset the integration period to the current month and year"""
        today = datetime.date.today()
        self.write({
            'integration_month': str(today.month).zfill(2),
            'integration_year': today.year,
        })

        month_name = dict(self._fields['integration_month'].selection).get(str(today.month).zfill(2))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Period Reset',
                'message': f'Reset to current period: {month_name} {today.year}',
                'type': 'success',
            }
        }


    def action_import_infopay_statements(self):
        """Import bank statements from Infopay API"""
        # Ensure dates are computed before proceeding
        self._compute_integration_dates()

        if not self.integration_start_date or not self.integration_end_date:
            raise UserError("Please select a month for integration before importing statements.")

        # Show confirmation message with period details
        month_name = dict(self._fields['integration_month'].selection).get(self.integration_month)
        start_date = self.integration_start_date.strftime('%B %d, %Y')
        end_date = self.integration_end_date.strftime('%B %d, %Y')

        # Ask for confirmation
        if not self.env.context.get('skip_confirmation'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Confirm Import',
                'res_model': 'bank.import.confirmation.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_bank_id': self.id,
                    'default_period_display': f"{month_name} {self.integration_year}",
                    'default_start_date': start_date,
                    'default_end_date': end_date,
                }
            }

        journals = self._get_bank_journals()
        for journal in journals:
            request_id = str(random.randint(100000000000000, 640812354371500))

            attachment = {
                'name': "Infopay Bank Statement Generation {} - {} {} {}".format(
                    request_id, month_name, self.integration_year,
                    "({} to {})".format(start_date, end_date)
                ),
                'raw': "",
            }

            # Create a transient attachment
            attachments = self.env['transient.attachment'].create(attachment)

            journal._import_bank_statement_custom(attachments)

        # Show success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Started',
                'message': f'Started importing transactions for {month_name} {self.integration_year} ({start_date} to {end_date})',
                'type': 'success',
            }
        }

    def _get_bank_journals(self):
        """Get bank journals and import transactions from Infopay"""
        if not self.infopay_client_id or not self.infopay_access_token:
            raise UserError("Infopay Client ID and Access Token must be configured.")

        journals = []

        try:
            # Ensure we have a valid session
            if not self._is_session_valid():
                self._create_infopay_session()

            # Get accounts from Infopay
            accounts_response = self._get_accounts_list()
            if not accounts_response:
                raise UserError("Failed to fetch accounts from Infopay API.")

            accounts = accounts_response.get('Accounts', [])

            # Process the accounts and import them into Odoo
            for account in accounts:
                iban = account.get('IBAN', '')
                account_id = account.get('AccountId', '')

                journal = self.env['account.journal'].search([('bank_account_id.acc_number', '=', iban)], limit=1)
                if not journal:
                    # Create a new journal if it doesn't exist
                    # Generate unique journal code using account ID or IBAN
                    account_code = account_id or iban.replace(' ', '').upper()[:10]

                    journal = self.env['account.journal'].create({
                        'name': account.get('AccountName', 'Infopay Account'),
                        'code': account_code,
                        'type': 'bank',
                        'bank_account_id': self.env['res.partner.bank'].create({
                            'acc_number': iban,
                            'bank_id': self.id,
                            'partner_id': self.env.company.partner_id.id,
                        }).id,
                    })

                # Get transactions for this account using configured date range
                transactions_response = self._get_transactions(
                    account_id,
                    self.integration_start_date,
                    self.integration_end_date
                )
                if not transactions_response:
                    continue

                transactions = transactions_response.get('Transactions', {})

                if not transactions:
                    continue

                booked_transactions = transactions.get('Booked', [])

                for tx in booked_transactions:
                    transaction_amount = tx.get('TransactionAmount', {})

                    vals = {
                        'transaction_id': tx.get('TransactionId'),
                        'booking_date': tx.get('BookingDate'),
                        'value_date': tx.get('ValueDate'),
                        'amount': transaction_amount.get('amount'),
                        'currency_id': self.env['res.currency'].search([('name', '=', transaction_amount.get('currency', 'BGN'))],
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

                journals.append(journal)

        except Exception as e:
            raise UserError("Infopay API Error: {}".format(e))
        finally:
            # Clean up session after operations
            self._cleanup_infopay_session()

        return journals

    def _is_session_valid(self):
        """Check if the current session is still valid"""
        if not self.infopay_session_id or not self.infopay_session_key:
            return False

        # For now, assume session is valid if we have both ID and key
        # In a real implementation, you might want to add a timestamp check
        return True

    def _create_infopay_session(self):
        """Create a new session with Infopay API"""
        url = "{}/api/session".format(self.infopay_api_url)

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "curl/7.68.0"
        }

        data = {
            "uniqueId": self.infopay_client_id,
            "accessToken": self.infopay_access_token
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            session_data = response.json()
            session_id = session_data.get("SessionId")
            sessin_key = session_data.get("SessionKey")

            if not session_id:
                raise UserError("Failed to create session with Infopay API.")

            # Update the record with new session
            self.write({
                'infopay_session_id': session_id,
                'infopay_session_key': sessin_key,
            })

            return session_id

        except requests.exceptions.RequestException as e:
            print("=== ERROR DETAILS ===")
            print("Error type: {}".format(type(e)))
            print("Error message: {}".format(str(e)))
            if hasattr(e, 'response'):
                print("Response status: {}".format(e.response.status_code))
                print("Response text: {}".format(e.response.text))
            raise UserError("Failed to create session with Infopay API: {}".format(e))

    def _cleanup_infopay_session(self):
        """Clean up the session with Infopay API"""
        if not self.infopay_session_id:
            return

        url = "{}/api/session/close".format(self.infopay_api_url)

        headers = {
            "accept": "application/json",
            "SessionId": self.infopay_session_id,
            "SessionKey": self.infopay_session_key,
            "User-Agent": "curl/7.68.0"
        }

        try:
            response = requests.post(url, headers=headers, timeout=30)
            # Don't raise error if cleanup fails, just log it
            if response.status_code == 200:
                # Clear session data
                self.write({
                    'infopay_session_id': False,
                    'infopay_session_key': False
                })
        except requests.exceptions.RequestException:
            # Ignore cleanup errors
            pass

    def _get_accounts_list(self):
        """Get list of accounts from Infopay API"""
        headers = {
            "accept": "application/json",
            "SessionId": self.infopay_session_id,
            "SessionKey": self.infopay_session_key,
            "User-Agent": "curl/7.68.0"
        }

        url = "{}/api/accounts".format(self.infopay_api_url)

        return self._execute_get_request(headers, url)

    def _get_transactions(self, account_id, date_from=None, date_to=None):
        """Get transactions for a specific account from Infopay API"""
        headers = {
            "accept": "application/json",
            "SessionId": self.infopay_session_id,
            "SessionKey": self.infopay_session_key,
            "User-Agent": "curl/7.68.0"
        }

        url = "{}/api/accounts/{}/transactions".format(self.infopay_api_url, account_id)

        # Add date filters and with_balance parameter as per Infopay API specification
        params = {
            'withBalance': 'true'  # Always include balance information
        }

        if date_from:
            params['dateFrom'] = date_from.isoformat() if hasattr(date_from, 'isoformat') else str(date_from)
        if date_to:
            params['dateTo'] = date_to.isoformat() if hasattr(date_to, 'isoformat') else str(date_to)

        return self._execute_get_request(headers, url, params)

    def _execute_get_request(self, headers, url, params=None):
        """Execute GET request to Infopay API with session handling"""
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 401:
                # Session might be expired, try to create a new one
                self._create_infopay_session()
                # Update headers with new session data using correct keys
                headers["SessionId"] = self.infopay_session_id
                headers["SessionKey"] = self.infopay_session_key
                response = requests.get(url, headers=headers, params=params, timeout=30)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise UserError("Failed to communicate with Infopay API: {}".format(e))

    def action_test_infopay_connection(self):
        """Test the connection to Infopay API"""
        try:
            if not self.infopay_client_id or not self.infopay_access_token:
                raise UserError("Infopay Client ID and Access Token must be configured.")

            # Test session creation
            self._create_infopay_session()

            # Test accounts endpoint
            accounts = self._get_accounts_list()

            # Clean up session
            self._cleanup_infopay_session()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Test',
                    'message': 'Successfully connected to Infopay API. Found {} accounts.'.format(
                        len(accounts.get('Accounts', []))
                    ),
                    'type': 'success',
                }
            }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Test Failed',
                    'message': str(e),
                    'type': 'danger',
                }
            }
