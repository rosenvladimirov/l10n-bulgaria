import datetime
import json
import random
import time

import requests

from odoo import fields, models
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

    # Bank-specific configuration
    bank_code = fields.Char(string="Bank Code")
    account_iban = fields.Char(string="Account IBAN")

    def action_import_infopay_statements(self):
        """Import bank statements from Infopay API"""
        journals = self._get_bank_journals()
        for journal in journals:
            request_id = str(random.randint(100000000000000, 640812354371500))

            attachment = {
                'name': "Infopay Bank Statement Generation {}".format(request_id),
                'raw': True,
            }

            # Create a transient attachment
            attachments = self.env['transient.attachment'].create(attachment)

            journal._import_bank_statement(attachments)

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

                # Get transactions for this account
                transactions_response = self._get_transactions(account_id)
                if not transactions_response:
                    continue

                transactions = transactions_response.get('Transactions', [])

                journal = self.env['account.journal'].search([('bank_account_id.acc_number', '=', iban)], limit=1)
                if not journal:
                    # Create a new journal if it doesn't exist
                    journal = self.env['account.journal'].create({
                        'name': account.get('AccountName', 'Infopay Account'),
                        'code': account.get('AccountCode', 'IPAY'),
                        'type': 'bank',
                        'bank_account_id': self.env['res.partner.bank'].create({
                            'acc_number': iban,
                            'bank_id': self.id,
                            'partner_id': self.env.user.partner_id.id,
                        }).id,
                    })

                for tx in transactions:
                    transaction_amount = tx.get('amount', {})

                    vals = {
                        'transaction_id': tx.get('id'),
                        'booking_date': tx.get('bookingDate'),
                        'value_date': tx.get('valueDate'),
                        'amount': transaction_amount.get('amount'),
                        'currency_id': self.env['res.currency'].search([('name', '=', transaction_amount.get('currency', 'BGN'))],
                                                                       limit=1).id,
                        'partner_name': tx.get('creditorName') or tx.get('debtorName'),
                        'ref': tx.get('description') or tx.get('id'),
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
        if not self.infopay_session_id or not self.infopay_session_expiry:
            return False

        # Check if session expires in the next 5 minutes
        from datetime import datetime, timedelta
        now = datetime.now()
        expiry = fields.Datetime.from_string(self.infopay_session_expiry)
        return now < expiry - timedelta(minutes=5)

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
            print(f"=== ERROR DETAILS ===")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text}")
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

        # Add date filters if provided
        params = {}
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to

        return self._execute_get_request(headers, url, params)

    def _execute_get_request(self, headers, url, params=None):
        """Execute GET request to Infopay API with session handling"""
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 401:
                # Session might be expired, try to create a new one
                self._create_infopay_session()
                headers["sessionId"] = self.infopay_session_id
                headers["sessionKey"] = self.infopay_session_key
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
