# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class HrVersion(models.Model):
    _inherit = 'hr.version'

    # =========================================================================
    # BULGARIAN LOCALIZATION FIELDS
    # =========================================================================

    # Insurance and social security
    l10n_bg_insurance_months = fields.Float(
        string='Insurance Months',
        help='Number of insurance months for social security calculations',
        default=0.0
    )

    # =========================================================================
    # CLASS SYSTEM (Класна система)
    # =========================================================================

    l10n_bg_initial_class_period = fields.Char(
        string='Starting Class Period (YY:MM:DD)',
        help='Initial class period in format YY:MM:DD',
        default='00:00:00'
    )

    l10n_bg_current_class_period = fields.Char(
        string='Current Class Period (YY:MM:DD)',
        compute='_compute_current_class_period',
        store=True,
        help='Current class period calculated from initial period and time worked'
    )

    l10n_bg_auto_class_increment = fields.Boolean(
        string='Automatic Class Increase',
        default=True,
        help='Automatically increment class period based on time worked'
    )

    l10n_bg_class_years_integer = fields.Integer(
        string='Class Years (Integer)',
        compute='_compute_class_years',
        store=True,
        help='Class years as integer value'
    )

    l10n_bg_class_years_decimal = fields.Float(
        string='Class Years (Decimal)',
        compute='_compute_class_years',
        store=True,
        digits=(12, 2),
        help='Class years in decimal format'
    )

    # =========================================================================
    # SENIORITY (Трудов стаж)
    # =========================================================================

    l10n_bg_seniority_years = fields.Float(
        string='Years of Work Experience',
        default=0.0,
        help='Total years of work experience for calculating allowances'
    )

    l10n_bg_seniority_allowance_rate = fields.Float(
        string='Seniority Allowance Rate (%)',
        default=0.0,
        help='Percentage rate for seniority allowance calculation'
    )

    l10n_bg_computed_seniority_allowance = fields.Monetary(
        string='Computed Seniority Allowance',
        compute='_compute_seniority_allowance',
        store=True,
        currency_field='currency_id',
        help='Automatically calculated seniority allowance'
    )

    # =========================================================================
    # MOD (Минимална осигурителна доход)
    # =========================================================================

    l10n_bg_computed_mod = fields.Monetary(
        string='Computed MOD',
        compute='_compute_mod',
        store=True,
        currency_field='currency_id',
        help='Computed minimum insurable income based on qualification and activity'
    )

    l10n_bg_manual_mod = fields.Monetary(
        string='Manual MOD Override',
        currency_field='currency_id',
        help='Manually set MOD value (overrides computed value)'
    )

    l10n_bg_effective_mod = fields.Monetary(
        string='Effective MOD',
        compute='_compute_mod',
        store=True,
        currency_field='currency_id',
        help='Final MOD value used for calculations'
    )

    l10n_bg_tzpb_rate = fields.Float(
        string='TZPB Rate (%)',
        default=0.4,
        help='Work accident and occupational disease fund rate'
    )

    # =========================================================================
    # NAP EXPORT (Агенция по заетостта)
    # =========================================================================

    l10n_bg_nap_export_status = fields.Selection([
        ('not_exported', 'Not Exported'),
        ('pending', 'Pending Export'),
        ('exported', 'Exported'),
        ('error', 'Export Error'),
    ], string='NAP Export Status',
        default='not_exported',
        help='Status of export to National Employment Agency')

    l10n_bg_nap_export_date = fields.Datetime(
        string='NAP Export Date',
        readonly=True,
        help='Date when contract was exported to NAP'
    )

    l10n_bg_nap_export_history_ids = fields.One2many(
        'l10n_bg.nap.export.history',
        'version_id',
        string='NAP Export History'
    )

    # =========================================================================
    # NSSI CERTIFICATES (БЛН)
    # =========================================================================

    l10n_bg_nssi_certificate_ids = fields.One2many(
        'hr.leave.nssi.certificate',
        'version_id',
        string='NSSI Certificates'
    )

    # =========================================================================
    # COMPUTED METHODS
    # =========================================================================

    @api.depends('l10n_bg_initial_class_period', 'contract_date_start', 'l10n_bg_auto_class_increment')
    def _compute_current_class_period(self):
        """Calculate current class period based on time worked"""
        for version in self:
            if not version.l10n_bg_auto_class_increment or not version.contract_date_start:
                version.l10n_bg_current_class_period = version.l10n_bg_initial_class_period or '00:00:00'
                continue

            try:
                # Parse initial period
                parts = (version.l10n_bg_initial_class_period or '00:00:00').split(':')
                initial_years = int(parts[0]) if len(parts) > 0 else 0
                initial_months = int(parts[1]) if len(parts) > 1 else 0
                initial_days = int(parts[2]) if len(parts) > 2 else 0

                # Calculate time worked
                end_date = version.contract_date_end or fields.Date.today()
                delta = relativedelta(end_date, version.contract_date_start)

                # Add worked time to an initial period
                total_years = initial_years + delta.years
                total_months = initial_months + delta.months
                total_days = initial_days + delta.days

                # Normalize (30 days = 1 month, 12 months = 1 year)
                if total_days >= 30:
                    total_months += total_days // 30
                    total_days = total_days % 30

                if total_months >= 12:
                    total_years += total_months // 12
                    total_months = total_months % 12

                version.l10n_bg_current_class_period = f"{total_years:02d}:{total_months:02d}:{total_days:02d}"

            except (ValueError, IndexError):
                version.l10n_bg_current_class_period = '00:00:00'

    @api.depends('l10n_bg_current_class_period')
    def _compute_class_years(self):
        """Calculate class years in integer and decimal format"""
        for version in self:
            try:
                parts = (version.l10n_bg_current_class_period or '00:00:00').split(':')
                years = int(parts[0]) if len(parts) > 0 else 0
                months = int(parts[1]) if len(parts) > 1 else 0
                days = int(parts[2]) if len(parts) > 2 else 0

                version.l10n_bg_class_years_integer = years
                version.l10n_bg_class_years_decimal = years + (months / 12.0) + (days / 360.0)

            except (ValueError, IndexError):
                version.l10n_bg_class_years_integer = 0
                version.l10n_bg_class_years_decimal = 0.0

    @api.depends('wage', 'l10n_bg_seniority_years', 'l10n_bg_seniority_allowance_rate')
    def _compute_seniority_allowance(self):
        """Calculate seniority allowance"""
        for version in self:
            if version.l10n_bg_seniority_allowance_rate > 0 and version.wage:
                version.l10n_bg_computed_seniority_allowance = (
                        version.wage * version.l10n_bg_seniority_allowance_rate / 100.0
                )
            else:
                version.l10n_bg_computed_seniority_allowance = 0.0

    @api.depends(
        'l10n_bg_qualification_group',
        'l10n_bg_economic_activity_code',
        'l10n_bg_manual_mod',
        'contract_date_start'
    )
    def _compute_mod(self):
        """Calculate MOD (Minimum Insurable Income)"""
        for version in self:
            if version.l10n_bg_manual_mod > 0:
                version.l10n_bg_effective_mod = version.l10n_bg_manual_mod
                version.l10n_bg_computed_mod = 0.0
            else:
                # Get MOD from rule parameters based on qualification and activity
                mod_value = self._get_mod_from_parameters(
                    version.l10n_bg_qualification_group,
                    version.l10n_bg_economic_activity_code,
                    version.contract_date_start or fields.Date.today()
                )
                version.l10n_bg_computed_mod = mod_value
                version.l10n_bg_effective_mod = mod_value

    def _get_mod_from_parameters(self, qualification, activity_code, reference_date):
        """Get MOD value from rule parameters"""
        # This should be implemented based on your MOD lookup logic
        # For now, return a default value
        default_mod = self.env['hr.rule.parameter']._get_parameter_from_code(
            'BG_DEFAULT_MOD',
            reference_date,
            raise_if_not_found=False
        )
        return default_mod or 933.0  # Default minimum wage for 2024

    # =========================================================================
    # BUSINESS METHODS
    # =========================================================================

    def get_class_info(self):
        """Get complete class information"""
        self.ensure_one()
        return {
            'initial_class_period': self.l10n_bg_initial_class_period,
            'current_class_period': self.l10n_bg_current_class_period,
            'class_years_integer': self.l10n_bg_class_years_integer,
            'class_years_decimal': self.l10n_bg_class_years_decimal,
            'auto_increment': self.l10n_bg_auto_class_increment,
            'seniority_years': self.l10n_bg_seniority_years,
        }

    def get_total_compensation(self):
        """Calculate total compensation including all allowances"""
        self.ensure_one()
        total = self.wage
        if self.l10n_bg_computed_seniority_allowance:
            total += self.l10n_bg_computed_seniority_allowance
        return total

    def get_mod_info(self):
        """Get MOD-related information"""
        self.ensure_one()
        return {
            'computed_mod': self.l10n_bg_computed_mod,
            'manual_override': self.l10n_bg_manual_mod,
            'effective_mod': self.l10n_bg_effective_mod,
            'tzpb_rate': self.l10n_bg_tzpb_rate,
            'qualification_group': self.l10n_bg_qualification_group,
            'economic_activity': self.l10n_bg_economic_activity_code,
        }

    def generate_nap_export_data(self):
        """Generate data structure for NAP export"""
        self.ensure_one()

        return {
            'employer_bulstat': self.company_id.l10n_bg_uic or '',
            'employ_type': '1',  # Regular employment
            'code_correction': '0',  # No correction
            'document_type': '1',  # Labor contract
            'employee_egn': self.employee_id.identification_id or '',
            'egn_type': '0',  # Bulgarian EGN
            'first_name': self.employee_id.name.split()[0] if self.employee_id.name else '',
            'second_name': self.employee_id.name.split()[1] if len(self.employee_id.name.split()) > 1 else '',
            'third_name': self.employee_id.name.split()[2] if len(self.employee_id.name.split()) > 2 else '',
            'contract_date': self.contract_date_start.strftime('%d.%m.%Y') if self.contract_date_start else '',
            'contract_type_code': self._get_contract_type_code(),
            'start_date': self.contract_date_start.strftime('%d.%m.%Y') if self.contract_date_start else '',
            'wage_amount': str(int(self.wage)) if self.wage else '0',
            'profession_code': self.l10n_bg_qualification_group.code if self.l10n_bg_qualification_group else '',
            'economic_activity_code': self.l10n_bg_economic_activity_code or '0000',
            'workplace_code': self.l10n_bg_workplace_code or '',
            'working_time_type': self.l10n_bg_working_time_type or '1',
            'daily_hours': str(int(self.l10n_bg_daily_hours)) if self.l10n_bg_daily_hours else '8',
            'basic_leave_days': str(self.l10n_bg_basic_leave_days),
        }

    def _get_contract_type_code(self):
        """Get contract type code for NAP export"""
        if self.l10n_bg_contract_duration_type == 'indefinite':
            return '1'
        elif self.l10n_bg_contract_duration_type == 'fixed_term':
            return '2'
        elif self.l10n_bg_contract_duration_type == 'specific_work':
            return '3'
        elif self.l10n_bg_contract_duration_type == 'replacement':
            return '4'
        return '1'

    def action_export_to_nap(self):
        """Export contract to NAP (National Employment Agency)"""
        self.ensure_one()

        # Create export history record
        export_history = self.env['l10n_bg.nap.export.history'].create({
            'version_id': self.id,
            'export_type': 'new_contract',
            'status': 'pending',
        })

        # Generate XML
        try:
            export_history.generate_nap_xml()
            self.write({
                'l10n_bg_nap_export_status': 'exported',
                'l10n_bg_nap_export_date': fields.Datetime.now(),
            })
        except Exception as e:
            export_history.write({
                'status': 'error',
                'error_message': str(e),
            })
            raise

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_bg.nap.export.history',
            'res_id': export_history.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================

    @api.constrains('l10n_bg_initial_class_period')
    def _check_class_period_format(self):
        """Validate class period format"""
        for version in self:
            if version.l10n_bg_initial_class_period:
                try:
                    parts = version.l10n_bg_initial_class_period.split(':')
                    if len(parts) != 3:
                        raise ValidationError(_('Class period must be in format YY:MM:DD'))

                    years = int(parts[0])
                    months = int(parts[1])
                    days = int(parts[2])

                    if months > 11 or months < 0:
                        raise ValidationError(_('Months must be between 0 and 11'))
                    if days > 29 or days < 0:
                        raise ValidationError(_('Days must be between 0 and 29'))

                except ValueError:
                    raise ValidationError(_('Class period must contain only numbers in format YY:MM:DD'))
