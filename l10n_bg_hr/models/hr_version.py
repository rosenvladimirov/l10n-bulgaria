# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class HrVersion(models.Model):
    _inherit = 'hr.version'

    work_location = fields.Char(
        string='Work Location Address',
        related='work_location_id.address_id.contact_address',
        readonly=True,
        store=True,
        help='Complete address of work location for contract display'
    )

    # Contract type specific to Bulgaria
    l10n_bg_contract_duration_type = fields.Selection(
        related='contract_type_id.l10n_bg_contract_duration_type',
        string='BG Contract Duration Type',
        store=True,
        readonly=True
    )
    l10n_bg_uic = fields.Char(
        related='company_id.l10n_bg_uic',
        string='Company UIC',
        readonly=True,
        store=True
    )

    # Employee identification
    l10n_bg_egn = fields.Char(
        related='employee_id.identification_id',
        string='EGN',
        readonly=True,
        store=True
    )

    # =========================================================================
    # PROFESSIONAL QUALIFICATIONS
    # =========================================================================

    l10n_bg_qualification_group = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='Qualification Group (NKPD)',
        help='Professional qualification according to NKPD nomenclature'
    )

    l10n_bg_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='Economic Activity (KID)',
        default=lambda self: self.env.company.l10n_bg_economic_activity_id,
        help='Economic activity according to KID 2008'
    )

    l10n_bg_economic_activity_code = fields.Char(
        string='Economic Activity Code',
        related='l10n_bg_economic_activity_id.code',
        store=True,
        readonly=True,
        help='Economic activity code according to KID 2008'
    )

    l10n_bg_workplace_code = fields.Char(
        string='Workplace Code (EKATTE)',
        help='Workplace location code according to EKATTE'
    )

    # =========================================================================
    # WORKING TIME
    # =========================================================================

    l10n_bg_working_time_type = fields.Selection([
        ('1', 'Normal Working Time'),
        ('2', 'Reduced Working Time'),
        ('3', 'Part-Time'),
        ('4', 'Flexible Working Time'),
        ('5', 'Shift Work'),
        ('6', 'Summarized Working Time'),
    ], string='Working Time Type',
        default='1',
        help='Type of working time organization')

    l10n_bg_daily_hours = fields.Float(
        string='Daily Hours',
        compute='_compute_daily_hours',
        store=True,
        help='Standard daily working hours'
    )

    # =========================================================================
    # LEAVE DAYS
    # =========================================================================

    l10n_bg_basic_leave_days = fields.Integer(
        string='Basic Annual Leave Days',
        default=20,
        help='Minimum annual leave days according to Bulgarian Labor Code'
    )

    l10n_bg_additional_leave_days = fields.Integer(
        string='Additional Leave Days',
        default=0,
        help='Additional annual leave days beyond basic entitlement'
    )

    l10n_bg_total_leave_days = fields.Integer(
        string='Total Annual Leave Days',
        compute='_compute_total_leave_days',
        store=True,
        help='Total annual leave days (basic + additional)'
    )

    # =========================================================================
    # CONTRACT AMENDMENTS
    # =========================================================================

    l10n_bg_amendment_ids = fields.One2many(
        'l10n_bg.hr.version.amendment',
        'version_id',
        string='Contract Amendments',
    )

    l10n_bg_amendment_count = fields.Integer(
        string='Amendment Count',
        compute='_compute_amendment_count',
    )

    @api.depends('l10n_bg_amendment_ids')
    def _compute_amendment_count(self):
        for version in self:
            version.l10n_bg_amendment_count = len(version.l10n_bg_amendment_ids)

    # =========================================================================
    # COMPUTED METHODS
    # =========================================================================

    @api.depends('resource_calendar_id.hours_per_day')
    def _compute_daily_hours(self):
        """Calculate daily working hours"""
        for version in self:
            if version.resource_calendar_id:
                version.l10n_bg_daily_hours = version.resource_calendar_id.hours_per_day
            else:
                version.l10n_bg_daily_hours = 8.0

    @api.depends('l10n_bg_basic_leave_days', 'l10n_bg_additional_leave_days')
    def _compute_total_leave_days(self):
        """Calculate total annual leave days"""
        for version in self:
            version.l10n_bg_total_leave_days = (
                    version.l10n_bg_basic_leave_days + version.l10n_bg_additional_leave_days
            )
