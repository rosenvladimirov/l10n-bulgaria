import datetime

from odoo import fields, models, api
from odoo.exceptions import UserError


class ResBank(models.Model):
    _inherit = 'res.bank'

    # InfoPay API Configuration
    infopay_api_url = fields.Char(string="Infopay API URL", default="https://integration.infopay.bg")
    infopay_client_id = fields.Char(string="Infopay Client ID")
    infopay_access_token = fields.Char(string="Infopay Access Token", store=True)

    # Session management
    infopay_session_id = fields.Char(string="Infopay Session ID", store=True)
    infopay_session_key = fields.Char(string="Infopay Session Key", store=True)

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

    def action_sync_global_config(self):
        """Sync this bank's configuration with global InfoPay settings"""
        config_settings = self.env['res.config.settings'].search([], limit=1)
        if not config_settings:
            raise UserError("Global InfoPay configuration not found.")
        
        if not config_settings.infopay_client_id or not config_settings.infopay_access_token:
            raise UserError("Global InfoPay configuration is incomplete. Please configure Client ID and Access Token in Settings.")
        
        # Update bank configuration with global settings
        self.write({
            'infopay_api_url': config_settings.infopay_api_url or self.infopay_api_url,
            'infopay_client_id': config_settings.infopay_client_id,
            'infopay_access_token': config_settings.infopay_access_token,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Configuration Synced',
                'message': 'Bank configuration has been synchronized with global InfoPay settings.',
                'type': 'success',
            }
        }

    def _validate_infopay_configuration(self):
        """Validate that InfoPay configuration is complete and valid"""
        if not self.infopay_client_id:
            raise UserError("Infopay Client ID must be configured for this bank.")
        
        if not self.infopay_access_token:
            raise UserError("Infopay Access Token must be configured for this bank.")
        
        if not self.infopay_api_url:
            raise UserError("Infopay API URL must be configured for this bank.")

    def is_infopay_configured(self):
        """Check if this bank is properly configured for InfoPay integration"""
        return bool(
            self.infopay_client_id and 
            self.infopay_access_token and 
            self.infopay_api_url
        )

    def can_import_infopay_statements(self):
        """Check if this bank can be used for importing InfoPay statements"""
        return self.is_infopay_configured() and self.integration_month and self.integration_year

    @api.model
    def create(self, vals):
        """Override create to automatically sync with global configuration if not provided"""
        record = super().create(vals)
        
        # If no InfoPay configuration is provided, try to sync with global settings
        if not vals.get('infopay_client_id') and not vals.get('infopay_access_token'):
            try:
                config_settings = self.env['res.config.settings'].search([], limit=1)
                if config_settings and config_settings.infopay_client_id and config_settings.infopay_access_token:
                    record.write({
                        'infopay_api_url': config_settings.infopay_api_url,
                        'infopay_client_id': config_settings.infopay_client_id,
                        'infopay_access_token': config_settings.infopay_access_token,
                    })
            except Exception:
                # Silently fail if global config is not available
                pass
        
        return record
