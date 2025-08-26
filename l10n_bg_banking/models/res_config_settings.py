import datetime

from odoo import fields, models, api
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # InfoPay API Configuration
    infopay_api_url = fields.Char(
        string="InfoPay API URL",
        config_parameter='l10n_bg_banking.infopay_api_url',
        default="https://integration.infopay.bg"
    )
    infopay_client_id = fields.Char(
        string="InfoPay Client ID",
        config_parameter='l10n_bg_banking.infopay_client_id'
    )
    infopay_access_token = fields.Char(
        string="InfoPay Access Token",
        config_parameter='l10n_bg_banking.infopay_access_token'
    )

    def action_start_infopay_import(self):
        """Start the InfoPay import wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'InfoPay Import',
            'res_model': 'bank.import.confirmation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_config_id': self.id,
            }
        }

    def action_clear_transactions(self):
        """Clear all imported transactions"""
        transactions = self.env['bank.transaction'].search([])
        count = len(transactions)
        transactions.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Transactions Cleared',
                'message': f'Successfully deleted {count} transactions.',
                'sticky': False,
            }
        }
