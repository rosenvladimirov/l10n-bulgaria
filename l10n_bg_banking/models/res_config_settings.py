import datetime
from odoo import fields, models, api
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # InfoPay API Configuration
    infopay_api_url = fields.Char(
        string="InfoPay API URL",
        config_parameter='l10n_bg_banking.infopay_api_url',
        default='https://integration.infopay.bg',
        help="Base URL for Infopay API integration"
    )
    
    infopay_client_id = fields.Char(
        string="Client ID",
        config_parameter='l10n_bg_banking.infopay_client_id',
        help="Your Infopay API Client ID"
    )
    
    infopay_access_token = fields.Char(
        string="Access Token",
        config_parameter='l10n_bg_banking.infopay_access_token',
        help="Your Infopay API Access Token"
    )

    # Integration Period Configuration
    integration_month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
        ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string="Integration Month", help="Month for transaction import")
    
    integration_year = fields.Integer(
        string="Integration Year",
        help="Year for transaction import"
    )

    # Computed Fields
    configured_journals_count = fields.Integer(
        string="Configured Journals",
        compute='_compute_infopay_status',
        store=False,
        help="Number of bank journals with IBAN configured"
    )
    
    infopay_status = fields.Selection([
        ('not_configured', 'Not Configured'),
        ('configured', 'Configured'),
        ('ready', 'Ready for Import')
    ], string="InfoPay Status",
        compute='_compute_infopay_status',
        store=False,
        help="Current status of InfoPay integration"
    )

    @api.model
    def get_values(self):
        """Get configuration values"""
        res = super().get_values()
        config_parameter = self.env['ir.config_parameter'].sudo()
        
        res.update(
            infopay_api_url=config_parameter.get_param('l10n_bg_banking.infopay_api_url', 'https://integration.infopay.bg'),
            infopay_client_id=config_parameter.get_param('l10n_bg_banking.infopay_client_id', ''),
            infopay_access_token=config_parameter.get_param('l10n_bg_banking.infopay_access_token', ''),
        )
        return res

    def set_values(self):
        """Set configuration values"""
        super().set_values()
        config_parameter = self.env['ir.config_parameter'].sudo()
        
        config_parameter.set_param('l10n_bg_banking.infopay_api_url', self.infopay_api_url or '')
        config_parameter.set_param('l10n_bg_banking.infopay_client_id', self.infopay_client_id or '')
        config_parameter.set_param('l10n_bg_banking.infopay_access_token', self.infopay_access_token or '')

    @api.depends('infopay_client_id', 'infopay_access_token')
    def _compute_infopay_status(self):
        """Compute the InfoPay configuration status"""
        for record in self:
            configured_journals = self._get_configured_journals()
            record.configured_journals_count = len(configured_journals)
            
            if not record.infopay_client_id or not record.infopay_access_token:
                record.infopay_status = 'not_configured'
            elif record.configured_journals_count == 0:
                record.infopay_status = 'configured'
            else:
                record.infopay_status = 'ready'

    def _get_configured_journals(self):
        """Get all bank journals that have bank accounts configured"""
        return self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('bank_account_id', '!=', False),
            ('bank_account_id.acc_number', '!=', False)
        ])

    def action_configure_journals(self):
        """Open account journal records for configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configure Bank Journals',
            'res_model': 'account.journal',
            'view_mode': 'list,form',
            'domain': [('type', '=', 'bank')],
            'context': {
                'default_type': 'bank',
                'search_default_bank': 1,
            },
            'target': 'current',
        }

    def validate_global_configuration(self):
        """Validate that the global InfoPay configuration is complete"""
        if not self.infopay_api_url:
            raise UserError("InfoPay API URL is not configured.")
        
        if not self.infopay_client_id:
            raise UserError("InfoPay Client ID is not configured.")
        
        if not self.infopay_access_token:
            raise UserError("InfoPay Access Token is not configured.")
