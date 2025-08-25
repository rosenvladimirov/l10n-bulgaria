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
    ], string="Integration Month", default=lambda self: str(datetime.date.today().month).zfill(2))

    # Year selection for integration
    integration_year = fields.Integer(
        string="Integration Year",
        default=lambda self: datetime.date.today().year
    )

    # Computed fields for display
    integration_period_display = fields.Char(
        string="Integration Period",
        compute='_compute_integration_period_display',
        store=False
    )

    @api.depends('integration_month', 'integration_year')
    def _compute_integration_period_display(self):
        """Compute human-readable period description"""
        for record in self:
            if record.integration_month and record.integration_year:
                month_name = dict(self._fields['integration_month'].selection).get(record.integration_month)
                record.integration_period_display = f"{month_name} {record.integration_year}"
            else:
                record.integration_period_display = "Not set"

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
                'default_integration_month': self.integration_month,
                'default_integration_year': self.integration_year,
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
                'message': f'Moved to: {month_name} {new_year}',
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
                'message': f'Moved to: {month_name} {new_year}',
                'type': 'success',
            }
        }

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
                'message': f'Set to current month: {dict(self._fields["integration_month"].selection).get(str(today.month).zfill(2))} {today.year}',
                'type': 'success',
            }
        }
