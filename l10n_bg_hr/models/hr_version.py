# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class HrVersion(models.Model):
    _inherit = 'hr.version'

    # =========================================================================
    # CONTRACT IDENTIFICATION (BG convention — separate from base `name`)
    # =========================================================================
    # Base `name` stays free text (Odoo standard). BG-specific labor contract
    # number is stored separately so it can be used in ETZ XML <contractno>
    # (cell 11) and legacy ERP integrations.

    l10n_bg_contract_number = fields.Char(
        string="Labor Contract Number",
        copy=False,
        index=True,
        help="Unique labor contract number. Auto-filled from ir.sequence "
             "'l10n_bg.contract.number' on create if empty. Used in the "
             "ETZ XML <contractno> element (cell 11).",
    )

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
        compute='_compute_l10n_bg_qualification_group',
        store=True,
        readonly=False,
        help='Professional qualification according to NKPD nomenclature. '
             'Auto-populated from the selected job position '
             '(hr.job.l10n_bg_ncop_position_id) but can be manually '
             'overridden.'
    )

    l10n_bg_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='Economic Activity (KID)',
        compute='_compute_l10n_bg_economic_activity_id',
        store=True,
        readonly=False,
        default=False,
        help='Economic activity according to KID 2008. Auto-populated '
             'from the selected job or company but can be overridden.'
    )

    @api.depends('job_id', 'job_id.l10n_bg_ncop_position_id')
    def _compute_l10n_bg_qualification_group(self):
        """Always mirrors the job's NKPD when job changes."""
        for version in self:
            if version.job_id and version.job_id.l10n_bg_ncop_position_id:
                version.l10n_bg_qualification_group = (
                    version.job_id.l10n_bg_ncop_position_id
                )

    @api.depends('job_id', 'job_id.l10n_bg_economic_activity_id', 'company_id')
    def _compute_l10n_bg_economic_activity_id(self):
        """Mirrors the job's КИД, falls back to company default."""
        for version in self:
            job_kid = (version.job_id.l10n_bg_economic_activity_id
                       if version.job_id else False)
            if job_kid:
                version.l10n_bg_economic_activity_id = job_kid
            elif (not version.l10n_bg_economic_activity_id
                  and version.company_id
                  and version.company_id.l10n_bg_economic_activity_id):
                version.l10n_bg_economic_activity_id = (
                    version.company_id.l10n_bg_economic_activity_id
                )

    def action_refresh_nkpd_kid(self):
        """Refresh НКПД and КИД from current job position."""
        for version in self:
            job = version.job_id
            if not job:
                continue
            vals = {}
            if job.l10n_bg_ncop_position_id:
                vals['l10n_bg_qualification_group'] = job.l10n_bg_ncop_position_id.id
            if job.l10n_bg_economic_activity_id:
                vals['l10n_bg_economic_activity_id'] = job.l10n_bg_economic_activity_id.id
            if vals:
                version.write(vals)

    @api.onchange('job_id')
    def _onchange_job_id_propagate_nkpd(self):
        """Instant UI feedback when user changes job in the form."""
        if self.job_id and self.job_id.l10n_bg_ncop_position_id:
            self.l10n_bg_qualification_group = (
                self.job_id.l10n_bg_ncop_position_id
            )
        if self.job_id and self.job_id.l10n_bg_economic_activity_id:
            self.l10n_bg_economic_activity_id = (
                self.job_id.l10n_bg_economic_activity_id
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

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-fill l10n_bg_contract_number from sequence if missing."""
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('l10n_bg_contract_number'):
                next_no = seq.next_by_code('l10n_bg.contract.number')
                if next_no:
                    vals['l10n_bg_contract_number'] = next_no
        return super().create(vals_list)

    def action_open_version(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.version',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'current',
        }
