import datetime
import random
import time
from configparser import ConfigParser

import requests

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import config


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

    psd2_oauth_url = fields.Char(string="PSD2 OAuth URL", store=False)
    psd2_base_url = fields.Char(string="PSD2 Base URL", store=False)
    psd2_accounts_api_url = fields.Char(string="PSD2 Accounts API URL", store=False)
    psd2_payments_api_url = fields.Char(string="PSD2 Accounts API URL", store=False)
    psd2_client_id = fields.Char(string="PSD2 Client ID", store=False)
    psd2_client_secret = fields.Char(string="PSD2 Client Secret", store=False)
    psd2_client_certificate_path = fields.Char(string="PSD2 Client Certificate Path", store=False)
    psd2_client_key_path = fields.Char(string="PSD2 Client Key Path", store=False)
    psd2_scope = fields.Char(string="PSD2 Scope", store=False)
    access_token = fields.Char(string="Access Token", store=True)

    psd2_bank_section_name = fields.Char(string="PSD2 Bank Section Name")

    def action_import_psd2_statements(self):
        journals = self._get_bank_journals()
        for journal in journals:
            request_id = str(random.randint(100000000000000, 640812354371500))

            attachment = {
                'name': f"PSD2 Bank Statement Generation {request_id}",
                'raw': True,
            }

            # Create a transient attachment
            attachments = self.env['transient.attachment'].create(attachment)

            journal._import_bank_statement(attachments)

    def _get_bank_journals(self):
        if not self.psd2_bank_section_name:
            return []

        journals = []

        if not self._load_config_settings():
            return journals

        try:
            if not self.access_token:
                self.access_token = self._get_access_token()

            # generate request ID random number
            request_id = str(random.randint(100000000000000, 640812354371500))
            # generate consent ID random number
            consent_id = str(random.randint(10000000000000, 76594129403900))

            accounts_response = self._get_accounts_list(request_id, consent_id)

            if not accounts_response:
                raise UserError("Failed to fetch accounts from PSD2 API.")

            accounts = accounts_response.json().get('accounts', [])

            # Process the accounts and import them into Odoo
            for account in accounts:
                iban = account.get('iban', '')
                transactions = account.get('_links', {}).get('transactions', {})
                transactions_href = transactions.get('href', '')

                transactions_json = self._get_transactions(transactions_href, request_id, consent_id).json()

                transactions = transactions_json.get('transactions', {})

                journal = self.env['account.journal'].search([('bank_account_id.acc_number', '=', iban)], limit=1)
                if not journal:
                    continue

                for tx in transactions.get('booked', []):
                    transaction_amount = tx.get('transactionAmount')

                    vals = {
                        'transaction_id': tx.get('transactionId'),
                        'booking_date': tx.get('bookingDate'),
                        'value_date': tx.get('valueDate'),
                        'amount': transaction_amount.get('amount'),
                        'currency_id': self.env['res.currency'].search([('name', '=', transaction_amount.get('currency'))],
                                                                       limit=1).id,
                        'partner_name': tx.get('creditorName', None) or tx.get('debtorName'),
                        'ref': tx.get('remittanceInformationUnstructured', None) or tx.get('transactionId'),
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
            raise UserError(f"PSD2 API Error: {e}")

        return journals

    def _get_access_token(self):
        url = self.psd2_oauth_url

        data = {
            "grant_type": "client_credentials",
            "scope": self.psd2_scope,
            "client_id": self.psd2_client_id,
            "client_secret": self.psd2_client_secret,
        }

        time.sleep(3)
        # Provide your cert and key files
        response = requests.post(
            url,
            data=data,
            cert=(self.psd2_client_certificate_path, self.psd2_client_key_path),
            verify=False
        )

        print("Status:", response.status_code)
        print("Response:", response.text)

        access_token = response.json().get("access_token")
        if not access_token:
            raise UserError("Failed to obtain access token from PSD2 API.")
        return access_token

    def _get_accounts_list(self, request_id, consent_id, recursion = 0):
        headers = {
            "Authorization": f'Bearer {self.access_token}',
            "X-Request-ID": request_id,
            "Consent-ID": consent_id,
            "Accept": "application/json"
        }

        url = f'{self.psd2_accounts_api_url}?withBalance=false'

        return self._execute_get_request(headers, url, recursion)

    def _get_transactions(self, url_path, request_id, consent_id, recursion = 0):
        headers = {
            "Authorization": f'Bearer {self.access_token}',
            "X-Request-ID": request_id,
            "Consent-ID": consent_id,
            "Accept": "application/json"
        }

        url = f'{self.psd2_base_url}{url_path}?bookingStatus=booked'

        return self._execute_get_request(headers, url, recursion)

    def _execute_get_request(self, headers, url, recursion):
        time.sleep(3)
        response = requests.get(url,
                                headers=headers,
                                cert=(self.psd2_client_certificate_path, self.psd2_client_key_path),
                                verify=False)
        if recursion > 1:
            return response
        if response.status_code == 401:
            self.access_token = self._get_access_token()
            headers["Authorization"] = f"Bearer {self.access_token}"
            return self._execute_get_request(headers, url, recursion + 1)
        return response

    def _load_config_settings(self):
        config_path = config.rcfile
        if not config_path:
            raise UserError("Configuration file not found.")
        parser = ConfigParser()
        parser.read(config_path)

        if not self.psd2_bank_section_name:
            return False

        section = f"bank:{self.psd2_bank_section_name}"
        if not parser.has_section(section):
            return False

        self.psd2_oauth_url = parser.get(section, 'psd2_oauth_url')
        self.psd2_base_url = parser.get(section, 'psd2_base_url')
        self.psd2_accounts_api_url = parser.get(section, 'psd2_accounts_api_url')
        self.psd2_payments_api_url = parser.get(section, 'psd2_payments_api_url')
        self.psd2_client_id = parser.get(section, 'psd2_client_id')
        self.psd2_client_secret = parser.get(section, 'psd2_client_secret')
        self.psd2_client_certificate_path = parser.get(section, 'psd2_client_certificate_path')
        self.psd2_client_key_path = parser.get(section, 'psd2_client_key_path')
        self.psd2_scope = parser.get(section, 'psd2_scope')
        return True
