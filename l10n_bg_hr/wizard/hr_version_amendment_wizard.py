# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


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
        compute='_compute_old_values', store=True, readonly=True,
    )
    new_wage = fields.Monetary(
        string='New Wage',
        currency_field='currency_id',
    )

    old_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='Current Position',
        compute='_compute_old_values', store=True, readonly=True,
    )
    new_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='New Position',
    )

    old_working_time_type = fields.Selection(selection=lambda self: self.env['hr.version'].fields_get(
            ['l10n_bg_working_time_type'])['l10n_bg_working_time_type']['selection'], string='Current Working Time',
        compute='_compute_old_values', store=True, readonly=True)

    new_working_time_type = fields.Selection(selection=lambda self: self.env['hr.version'].fields_get(
            ['l10n_bg_working_time_type'])['l10n_bg_working_time_type']['selection'], string='New Working Time')

    old_leave_days = fields.Integer(string='Current Leave Days',
        compute='_compute_old_values', store=True, readonly=True)
    new_leave_days = fields.Integer(string='New Leave Days')

    old_work_location = fields.Char(string='Current Work Location',
        compute='_compute_old_values', store=True, readonly=True)
    new_work_location = fields.Char(string='New Work Location')

    # DEF-116: досега уизардът можеше да смени ЕТИКЕТА на работното време, но
    # нямаше къде да се въведат часовете — а те определят и календара, и
    # прората на МОД. Без тях „непълно работно време" е дума без число.
    old_weekly_hours = fields.Float(string='Current Weekly Hours',
        compute='_compute_old_values', store=True, readonly=True)
    new_weekly_hours = fields.Float(string='New Weekly Hours',
        help='Contracted weekly hours. Determines the working time calendar '
             'and the pro-rated minimum insurance income.')
    old_daily_hours = fields.Float(string='Current Daily Hours',
        compute='_compute_old_values', store=True, readonly=True)
    new_daily_hours = fields.Float(string='New Daily Hours')

    # 🔑 Без крайна дата срочното ДС ражда ПОСТОЯННА версия: изтичащият крон
    # търси `date_end`, не го намира и командироването не свършва никога.
    # Дотук визардът изобщо не пълнеше нито датата, нито флаговете — тоест
    # един и същ бизнес факт минаваше през формата и през визарда с РАЗЛИЧЕН
    # изход.
    date_end = fields.Date(
        string='End Date',
        help="When a temporary assignment stops being in force. Required for "
             "temporary assignments — the expiry cron looks for it.",
    )

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.version_id:
            self.version_id = self.employee_id.version_id

    @api.depends('version_id')
    def _compute_old_values(self):
        # DEF-21: попълваме old_* server-side през compute(store=True), за да
        # стигнат до action_create_amendment. readonly Python полета не се
        # изпращат от web client-а при save на transient → onchange стойностите
        # се губеха и amendment-ите записваха old_wage=0.
        for wiz in self:
            v = wiz.version_id
            wiz.old_wage = v.wage if v else 0.0
            wiz.old_position_id = v.l10n_bg_qualification_group if v else False
            wiz.old_working_time_type = v.l10n_bg_working_time_type if v else False
            wiz.old_leave_days = v.l10n_bg_total_leave_days if v else 0
            wiz.old_work_location = (v.work_location or '') if v else ''
            wiz.old_daily_hours = v.l10n_bg_daily_hours if v else 0.0
            wiz.old_weekly_hours = (
                v.l10n_bg_weekly_hours
                if v and 'l10n_bg_weekly_hours' in v._fields else 0.0)

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
        if self.new_weekly_hours:
            vals['new_weekly_hours'] = self.new_weekly_hours
        if self.new_daily_hours:
            vals['new_daily_hours'] = self.new_daily_hours

        if self.amendment_type == 'temporary_assignment':
            if not self.date_end:
                raise ValidationError(_(
                    "A temporary assignment needs an end date. Without it the "
                    "change would stay in force forever."))
            # Флаговете НЕ идват от onchange: той не се изпълнява при create
            # през RPC или импорт, а гардът и изтичащият крон стъпват точно
            # на тях.
            vals.update({
                'is_temporary': True,
                'is_temporary_assignment': True,
                'date_end': self.date_end,
            })

        amendment = self.env['l10n_bg.hr.version.amendment'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_bg.hr.version.amendment',
            'res_id': amendment.id,
            'view_mode': 'form',
            'target': 'current',
        }
