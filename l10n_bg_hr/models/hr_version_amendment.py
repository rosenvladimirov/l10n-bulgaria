# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrContractAmendment(models.Model):
    _name = 'l10n_bg.hr.version.amendment'
    _description = 'Contract Amendment (BG)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'amendment_date desc, id desc'

    # Basic fields
    name = fields.Char(
        string='Amendment Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )

    version_id = fields.Many2one(
        'hr.version',
        string='Contract',
        required=True,
        ondelete='cascade',
        domain="[('employee_id', '!=', False)]",
        tracking=True
    )

    employee_id = fields.Many2one(
        related='version_id.employee_id',
        string='Employee',
        readonly=True,
        store=True
    )

    company_id = fields.Many2one(
        related='version_id.company_id',
        string='Company',
        readonly=True,
        store=True
    )

    # Amendment details
    amendment_date = fields.Date(
        string='Amendment Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Date when the amendment takes effect'
    )

    amendment_type = fields.Selection([
        ('wage', 'Wage Change'),
        ('position', 'Position Change'),
        ('working_time', 'Working Time Change'),
        ('leave_days', 'Leave Days Change'),
        ('class_period', 'Class Period Change'),
        ('workplace', 'Workplace Change'),
        ('other', 'Other Amendment'),
    ], string='Amendment Type',
        required=True,
        tracking=True,
        help='Type of contract amendment'
    )

    description = fields.Text(
        string='Description',
        required=True,
        tracking=True,
        help='Detailed description of the amendment'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('applied', 'Applied'),
        ('cancelled', 'Cancelled'),
    ], string='Status',
        default='draft',
        required=True,
        tracking=True
    )

    # Changed fields tracking
    wage_before = fields.Monetary(
        string='Wage Before',
        currency_field='currency_id',
        readonly=True
    )

    wage_after = fields.Monetary(
        string='Wage After',
        currency_field='currency_id'
    )

    position_before = fields.Char(
        string='Position Before',
        readonly=True
    )

    position_after = fields.Char(
        string='Position After'
    )

    working_hours_before = fields.Float(
        string='Working Hours Before',
        readonly=True
    )

    working_hours_after = fields.Float(
        string='Working Hours After'
    )

    leave_days_before = fields.Integer(
        string='Leave Days Before',
        readonly=True
    )

    leave_days_after = fields.Integer(
        string='Leave Days After'
    )

    class_period_before = fields.Char(
        string='Class Period Before',
        readonly=True
    )

    class_period_after = fields.Char(
        string='Class Period After'
    )

    # Technical fields
    currency_id = fields.Many2one(
        related='version_id.currency_id',
        readonly=True
    )

    # NAP export
    l10n_bg_nap_export_status = fields.Selection([
        ('not_exported', 'Not Exported'),
        ('pending', 'Pending Export'),
        ('exported', 'Exported'),
        ('error', 'Export Error'),
    ], string='NAP Export Status',
        default='not_exported',
        help='Status of export to National Employment Agency'
    )

    l10n_bg_nap_export_date = fields.Datetime(
        string='NAP Export Date',
        readonly=True
    )

    # =========================================================================
    # ORM METHODS
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('l10n_bg.hr.version.amendment') or _('New')
        return super().create(vals_list)

    @api.onchange('version_id')
    def _onchange_version_id(self):
        """Load current contract values"""
        if self.version_id:
            self.wage_before = self.version_id.wage
            self.working_hours_before = self.version_id.resource_calendar_id.hours_per_day if self.version_id.resource_calendar_id else 8.0
            self.leave_days_before = self.version_id.l10n_bg_total_leave_days
            self.class_period_before = self.version_id.l10n_bg_current_class_period
            self.position_before = self.version_id.job_id.name if self.version_id.job_id else ''

    @api.onchange('amendment_type')
    def _onchange_amendment_type(self):
        """Set default values based on amendment type"""
        if self.amendment_type and self.version_id:
            if self.amendment_type == 'wage':
                self.wage_after = self.wage_before
            elif self.amendment_type == 'working_time':
                self.working_hours_after = self.working_hours_before
            elif self.amendment_type == 'leave_days':
                self.leave_days_after = self.leave_days_before
            elif self.amendment_type == 'class_period':
                self.class_period_after = self.class_period_before
            elif self.amendment_type == 'position':
                self.position_after = self.position_before

    # =========================================================================
    # BUSINESS METHODS
    # =========================================================================

    def action_confirm(self):
        """Confirm the amendment"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_('Only draft amendments can be confirmed'))

        self.write({'state': 'confirmed'})
        return True

    def action_apply(self):
        """Apply the amendment to the contract"""
        self.ensure_one()

        if self.state not in ['confirmed', 'draft']:
            raise ValidationError(_('Only confirmed or draft amendments can be applied'))

        # Prepare update values
        vals = {}

        if self.amendment_type == 'wage' and self.wage_after:
            vals['wage'] = self.wage_after

        elif self.amendment_type == 'working_time' and self.working_hours_after:
            # Note: This might need adjustment based on how working hours are stored
            # in the resource.calendar
            pass

        elif self.amendment_type == 'leave_days' and self.leave_days_after:
            vals['l10n_bg_basic_leave_days'] = self.leave_days_after

        elif self.amendment_type == 'class_period' and self.class_period_after:
            vals['l10n_bg_initial_class_period'] = self.class_period_after

        elif self.amendment_type == 'position' and self.position_after:
            # Find job by name or handle differently
            job = self.env['hr.job'].search([('name', '=', self.position_after)], limit=1)
            if job:
                vals['job_id'] = job.id

        # Apply changes to contract
        if vals:
            self.version_id.write(vals)

        self.write({
            'state': 'applied',
        })

        # Create message on contract
        self.version_id.message_post(
            body=_('Amendment applied: %s - %s') % (self.name, self.description)
        )

        return True

    def action_cancel(self):
        """Cancel the amendment"""
        self.ensure_one()

        if self.state == 'applied':
            raise ValidationError(_('Applied amendments cannot be cancelled'))

        self.write({'state': 'cancelled'})
        return True

    def action_export_to_nap(self):
        """Export amendment to NAP"""
        self.ensure_one()

        if self.state != 'applied':
            raise ValidationError(_('Only applied amendments can be exported to NAP'))

        # Create export history record
        export_history = self.env['l10n_bg.nap.export.history'].create({
            'version_id': self.version_id.id,
            'contract_amendment_id': self.id,
            'export_type': 'contract_amendment',
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

    def generate_nap_export_data(self):
        """Generate data for NAP export"""
        self.ensure_one()

        # Start with contract data
        data = self.version_id.generate_nap_export_data()

        # Update with amendment-specific data
        data.update({
            'employ_type': '2',  # Amendment
            'amendment_date': self.amendment_date.strftime('%d.%m.%Y') if self.amendment_date else '',
        })

        return data

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================

    @api.constrains('amendment_date', 'version_id')
    def _check_amendment_date(self):
        """Validate amendment date"""
        for amendment in self:
            if amendment.version_id.contract_date_start and amendment.amendment_date < amendment.version_id.contract_date_start:
                raise ValidationError(
                    _('Amendment date cannot be before contract start date')
                )

    @api.constrains('class_period_after')
    def _check_class_period_format(self):
        """Validate class period format"""
        for amendment in self:
            if amendment.class_period_after:
                try:
                    parts = amendment.class_period_after.split(':')
                    if len(parts) != 3:
                        raise ValidationError(_('Class period must be in format YY:MM:DD'))

                    int(parts[0])  # years
                    int(parts[1])  # months
                    int(parts[2])  # days

                except (ValueError, IndexError):
                    raise ValidationError(_('Class period must contain only numbers in format YY:MM:DD'))
