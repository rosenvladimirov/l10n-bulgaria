# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrVersionAmendmentWizard(models.TransientModel):
    _name = 'l10n_bg.hr.version.amendment.wizard'
    _description = 'New Contract Amendment Wizard'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        default=lambda self: self.env.context.get('active_id'),
    )

    version_id = fields.Many2one(
        'hr.version',
        string='Contract Version',
        required=True,
        domain="[('employee_id', '=', employee_id)]",
    )

    amendment_type = fields.Selection([
        ('wage_change', 'Wage Change'),
        ('position_change', 'Position Change'),
        ('workplace_change', 'Workplace Change'),
        ('working_time_change', 'Working Time Change'),
        ('leave_change', 'Leave Days Change'),
        ('temporary_assignment', 'Temporary Assignment'),
        ('contract_extension', 'Contract Extension'),
        ('additional_duties', 'Additional Duties'),
        ('other', 'Other Amendment'),
    ], string='Amendment Type',
        required=True,
    )

    subject = fields.Char(
        string='Subject',
        required=True,
    )

    date_effective = fields.Date(
        string='Effective Date',
        required=True,
        default=fields.Date.today,
    )

    # --- Before values (readonly, populated on version change) ---
    currency_id = fields.Many2one(
        related='version_id.currency_id',
        readonly=True,
    )

    old_wage = fields.Monetary(
        string='Current Wage',
        currency_field='currency_id',
        readonly=True,
    )
    new_wage = fields.Monetary(
        string='New Wage',
        currency_field='currency_id',
    )

    old_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='Current Position',
        readonly=True,
    )
    new_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='New Position',
    )

    old_working_time_type = fields.Selection([
        ('1', 'Normal Working Time'),
        ('2', 'Reduced Working Time'),
        ('3', 'Part-Time'),
        ('4', 'Flexible Working Time'),
        ('5', 'Shift Work'),
        ('6', 'Summarized Working Time'),
    ], string='Current Working Time', readonly=True)

    new_working_time_type = fields.Selection([
        ('1', 'Normal Working Time'),
        ('2', 'Reduced Working Time'),
        ('3', 'Part-Time'),
        ('4', 'Flexible Working Time'),
        ('5', 'Shift Work'),
        ('6', 'Summarized Working Time'),
    ], string='New Working Time')

    old_leave_days = fields.Integer(string='Current Leave Days', readonly=True)
    new_leave_days = fields.Integer(string='New Leave Days')

    old_work_location = fields.Char(string='Current Work Location', readonly=True)
    new_work_location = fields.Char(string='New Work Location')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.version_id:
            self.version_id = self.employee_id.version_id

    @api.onchange('version_id')
    def _onchange_version_id(self):
        if self.version_id:
            v = self.version_id
            self.old_wage = v.wage
            self.old_position_id = v.l10n_bg_qualification_group
            self.old_working_time_type = v.l10n_bg_working_time_type
            self.old_leave_days = v.l10n_bg_total_leave_days
            self.old_work_location = v.work_location or ''

    def action_create_amendment(self):
        self.ensure_one()
        vals = {
            'version_id': self.version_id.id,
            'amendment_type': self.amendment_type,
            'subject': self.subject,
            'date_effective': self.date_effective,
            'date_signed': fields.Date.today(),
            'old_wage': self.old_wage,
            'old_position_id': self.old_position_id.id if self.old_position_id else False,
            'old_working_time_type': self.old_working_time_type,
            'old_leave_days': self.old_leave_days,
            'old_work_location': self.old_work_location,
            'old_economic_activity_id': self.version_id.l10n_bg_economic_activity_id.id if self.version_id.l10n_bg_economic_activity_id else False,
            'old_daily_hours': self.version_id.l10n_bg_daily_hours,
            'old_weekly_hours': self.version_id.l10n_bg_weekly_hours if 'l10n_bg_weekly_hours' in self.version_id._fields else 40.0,
        }
        if self.new_wage:
            vals['new_wage'] = self.new_wage
        if self.new_position_id:
            vals['new_position_id'] = self.new_position_id.id
        if self.new_working_time_type:
            vals['new_working_time_type'] = self.new_working_time_type
        if self.new_leave_days:
            vals['new_leave_days'] = self.new_leave_days
        if self.new_work_location:
            vals['new_work_location'] = self.new_work_location

        amendment = self.env['l10n_bg.hr.version.amendment'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_bg.hr.version.amendment',
            'res_id': amendment.id,
            'view_mode': 'form',
            'target': 'current',
        }
