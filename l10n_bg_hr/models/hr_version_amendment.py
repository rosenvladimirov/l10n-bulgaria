# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class L10nBGHrVersionAmendment(models.Model):
    """Допълнително споразумение към трудовия договор (чл. 118 КТ)"""
    _name = 'l10n_bg.hr.version.amendment'
    _description = 'Contract Amendment'
    _order = 'date_signed desc, id desc'
    _rec_name = 'amendment_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_domain = models.check_company_domain_parent_of

    # =========================================================================
    # ОСНОВНИ ПОЛЕТА
    # =========================================================================

    amendment_number = fields.Char(
        string='Amendment Number',
        copy=False,
        default=lambda self: _('New'),
        readonly=True,
        index=True,
    )

    version_id = fields.Many2one(
        'hr.version',
        string='Contract Version',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
        domain="[('employee_id', '!=', False)]",
    )

    employee_id = fields.Many2one(
        related='version_id.employee_id',
        string='Employee',
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        related='version_id.company_id',
        string='Company',
        store=True,
        readonly=True,
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
        tracking=True,
    )

    # =========================================================================
    # ДАТИ И ВАЛИДНОСТ
    # =========================================================================

    date_signed = fields.Date(
        string='Date Signed',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )

    date_effective = fields.Date(
        string='Effective Date',
        required=True,
        tracking=True,
    )

    date_end = fields.Date(
        string='End Date',
    )

    is_temporary = fields.Boolean(
        string='Temporary Amendment',
        default=False,
    )

    # =========================================================================
    # СЪДЪРЖАНИЕ
    # =========================================================================

    subject = fields.Char(
        string='Subject',
        required=True,
        translate=True,
    )

    description = fields.Html(
        string='Amendment Details',
        translate=True,
    )

    legal_basis = fields.Text(
        string='Legal Basis',
        translate=True,
    )

    # =========================================================================
    # ПРОМЕНИ — ЗАПЛАТА
    # =========================================================================

    old_wage = fields.Monetary(
        string='Previous Wage',
        currency_field='currency_id',
        readonly=True,
    )

    new_wage = fields.Monetary(
        string='New Wage',
        currency_field='currency_id',
    )

    wage_change_reason = fields.Text(string='Wage Change Reason')

    wage_difference = fields.Monetary(
        string='Wage Difference',
        compute='_compute_wage_difference',
        currency_field='currency_id',
    )

    is_wage_increase = fields.Boolean(
        string='Wage Increase',
        compute='_compute_wage_difference',
    )

    # =========================================================================
    # ПРОМЕНИ — ПОЗИЦИЯ (НКПД)
    # =========================================================================

    old_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='Previous NKPD Position',
        readonly=True,
    )

    new_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='New NKPD Position',
    )

    # =========================================================================
    # ПРОМЕНИ — ИКОНОМИЧЕСКА ДЕЙНОСТ (КИД)
    # =========================================================================

    old_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='Previous Economic Activity',
        readonly=True,
    )

    new_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='New Economic Activity',
    )

    # =========================================================================
    # ПРОМЕНИ — РАБОТНО ВРЕМЕ
    # =========================================================================

    old_working_time_type = fields.Selection(selection=lambda self: self.env['hr.version'].fields_get(
            ['l10n_bg_working_time_type'])['l10n_bg_working_time_type']['selection'], string='Previous Working Time Type', readonly=True)

    new_working_time_type = fields.Selection(selection=lambda self: self.env['hr.version'].fields_get(
            ['l10n_bg_working_time_type'])['l10n_bg_working_time_type']['selection'], string='New Working Time Type')

    old_daily_hours = fields.Float(string='Previous Daily Hours', readonly=True)
    new_daily_hours = fields.Float(string='New Daily Hours')

    old_weekly_hours = fields.Float(string='Previous Weekly Hours', readonly=True)
    new_weekly_hours = fields.Float(string='New Weekly Hours')

    # =========================================================================
    # ПРОМЕНИ — РАБОТНО МЯСТО
    # =========================================================================

    old_work_location = fields.Char(string='Previous Work Location', readonly=True)
    new_work_location = fields.Char(string='New Work Location')

    # =========================================================================
    # ПРОМЕНИ — ОТПУСКИ
    # =========================================================================

    old_leave_days = fields.Integer(string='Previous Leave Days', readonly=True)
    new_leave_days = fields.Integer(string='New Leave Days')

    # =========================================================================
    # ВРЕМЕННО ПРЕМЕСТВАНЕ (ЧЛ. 106-114 КТ)
    # =========================================================================

    is_temporary_assignment = fields.Boolean(string='Temporary Assignment')

    temporary_assignment_reason = fields.Selection([
        ('production_necessity', 'Production Necessity'),
        ('employee_replacement', 'Employee Replacement'),
        ('urgent_work', 'Urgent Work'),
        ('natural_disaster', 'Natural Disaster'),
        ('other_emergency', 'Other Emergency'),
    ], string='Assignment Reason')

    assignment_duration_months = fields.Integer(string='Assignment Duration (months)')
    assignment_location = fields.Char(string='Assignment Location')
    assignment_compensation = fields.Monetary(
        string='Assignment Compensation',
        currency_field='currency_id',
    )

    # =========================================================================
    # СТАТУС И ОДОБРЕНИЯ
    # =========================================================================

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancel', 'Cancelled'),
    ], string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    approved_by_id = fields.Many2one('res.users', string='Approved by', readonly=True)
    approved_date = fields.Datetime(string='Approval Date', readonly=True)

    signed_by_employee = fields.Boolean(string='Signed by Employee')
    signed_by_employer = fields.Boolean(string='Signed by Employer')

    # =========================================================================
    # ТЕХНИЧЕСКИ ПОЛЕТА
    # =========================================================================

    currency_id = fields.Many2one(
        related='version_id.currency_id',
        string='Currency',
        readonly=True,
    )

    notes = fields.Text(string='Internal Notes')

    # =========================================================================
    # COMPUTED
    # =========================================================================

    @api.depends('amendment_number', 'subject')
    def _compute_display_name(self):
        for rec in self:
            if rec.amendment_number and rec.amendment_number != _('New') and rec.subject:
                rec.display_name = f"{rec.amendment_number} - {rec.subject}"
            else:
                rec.display_name = rec.amendment_number or _('New Amendment')

    @api.depends('new_wage', 'old_wage')
    def _compute_wage_difference(self):
        for rec in self:
            if rec.new_wage and rec.old_wage:
                rec.wage_difference = rec.new_wage - rec.old_wage
                rec.is_wage_increase = rec.wage_difference > 0
            else:
                rec.wage_difference = 0.0
                rec.is_wage_increase = False

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================

    @api.constrains('date_signed', 'date_effective')
    def _check_dates(self):
        for rec in self:
            if rec.date_signed and rec.date_effective and rec.date_signed > rec.date_effective:
                raise ValidationError(
                    _("Signature date cannot be after effective date."))

    @api.constrains('date_effective', 'date_end')
    def _check_effective_dates(self):
        for rec in self:
            if rec.date_end and rec.date_effective and rec.date_effective >= rec.date_end:
                raise ValidationError(
                    _("Effective date must be before end date."))

    @api.constrains('assignment_duration_months')
    def _check_assignment_duration(self):
        for rec in self:
            if rec.is_temporary_assignment and rec.assignment_duration_months and rec.assignment_duration_months > 12:
                raise ValidationError(
                    _("Temporary assignment cannot exceed 12 months per Labor Code."))

    # =========================================================================
    # ORM
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('amendment_number', _('New')) == _('New'):
                vals['amendment_number'] = self.env['ir.sequence'].next_by_code(
                    'l10n_bg.hr.version.amendment') or _('New')
        return super().create(vals_list)

    # =========================================================================
    # ACTIONS
    # =========================================================================

    def action_submit_for_approval(self):
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_("Only draft amendments can be submitted."))
        self.state = 'to_approve'

    def action_approve(self):
        self.ensure_one()
        if self.state != 'to_approve':
            raise ValidationError(_("Only amendments pending approval can be approved."))
        vals = {
            'state': 'approved',
            'approved_by_id': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        }
        # Щампова „предишната стойност" при одобрението. onchange-ът лови
        # само пътя през интерфейса — при импорт или RPC old_* оставаха
        # празни и бланката излизаше без предишната стойност. Пълним само
        # незаетите, за да не се презапише ръчно въведена стойност.
        vals.update({
            field_name: value
            for field_name, value in self._snapshot_old_values().items()
            if not self[field_name]
        })
        self.write(vals)

    def action_activate(self):
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_("Only approved amendments can be activated."))
        self._apply_version_changes()
        self.state = 'active'

    def action_cancel(self):
        self.ensure_one()
        if self.state in ('active', 'expired'):
            raise ValidationError(_("Cannot cancel active or expired amendments."))
        self.state = 'cancel'

    # =========================================================================
    # BUSINESS LOGIC
    # =========================================================================

    def _apply_version_changes(self):
        """Apply amendment changes as a NEW version starting on the effective date."""
        self.ensure_one()

        # Срочните ДС искат и обратен ход при изтичане, а
        # cron_expire_temporary_amendments още пише върху текущата версия.
        # Докато изходът не е решен, не ги пускаме по новия път — иначе
        # входът създава версия, а изходът презаписва, и остава наполовина.
        if self.is_temporary or self.is_temporary_assignment:
            raise ValidationError(_(
                "Activating temporary amendments is not supported yet: the "
                "expiry path still writes back onto the current version. "
                "Please contact your administrator."))

        vals = {}

        if self.new_wage:
            vals['wage'] = self.new_wage
        if self.new_position_id:
            vals['l10n_bg_qualification_group'] = self.new_position_id.id
        if self.new_economic_activity_id:
            vals['l10n_bg_economic_activity_id'] = self.new_economic_activity_id.id
        if self.new_working_time_type:
            vals['l10n_bg_working_time_type'] = self.new_working_time_type
        if self.new_work_location:
            vals['work_location'] = self.new_work_location
        if self.new_leave_days:
            vals['l10n_bg_basic_leave_days'] = self.new_leave_days
        if self.new_weekly_hours and 'l10n_bg_weekly_hours' in self.version_id._fields:
            vals['l10n_bg_weekly_hours'] = self.new_weekly_hours

        if not vals:
            return

        # Промяната ражда НОВА версия от датата на влизане в сила, вместо да
        # презаписва текущата. Иначе увеличение с бъдеща дата важи и назад, а
        # преизчисляване на минал период (Д1 корекция, УП-2, регенерация на
        # регистъра) чете новата стойност като валидна открай време.
        # 🚨 Полета с copy=False се губят: create_version стъпва на copy_data().
        # `copy=False` е предвидено за ДУБЛИРАНЕ на версия (нов договор), но при
        # допълнително споразумение договорът е СЪЩИЯТ — стажът и номерът му
        # продължават. Без това новата версия тръгва с нулев клас: наблюдавано
        # на plm_acc (v939 class_period 15:09:06 → v1116 00:00:00, class_years
        # 15 → 0), тоест ДТВ-то за втория сегмент падаше на нула.
        carried = {}
        for field_name in ('l10n_bg_current_class_period',
                           'l10n_bg_unrecognized_company_is_manual',
                           'l10n_bg_contract_number'):
            if field_name in self.version_id._fields:
                carried[field_name] = self.version_id[field_name]

        employee = self.version_id.employee_id
        new_version = employee.create_version(
            dict(vals, date_version=self.date_effective))
        if carried:
            new_version.write(carried)
        # 🚨 create_version излиза рано и НЕ прилага стойностите, когато вече
        # съществува версия с тази дата — тогава връща нея непокътната. Без
        # изричния write ДС-то минава в „в сила", а заплатата не се сменя, тихо.
        new_version.write(vals)
        new_version.message_post(
            body=_('Created by amendment %s') % self.amendment_number,
            subject=_('Contract Amendment Applied'),
        )

    @api.model
    def cron_activate_due_amendments(self):
        """Активира одобрените ДС, чиято дата на влизане в сила е настъпила.

        Активирането беше само ръчен бутон. ДС се подписва предварително, с
        бъдеща дата, и между одобрението и датата минават седмици — пропусне
        ли се натискането, фишът излиза със старата заплата и мълчи.
        Симетрично на cron_expire_temporary_amendments: ако изтичането върви,
        а активирането не, срочните ДС ще изтичат, без изобщо да са влизали
        в сила.
        """
        today = fields.Date.today()
        due = self.search([
            ('state', '=', 'approved'),
            ('date_effective', '<=', today),
        ])
        for amendment in due:
            # Грешка от едно ДС не спира партидата — остава в „Одобрено"
            # с бележка в чата, за да се види от кого се чака намеса.
            try:
                with self.env.cr.savepoint():
                    amendment.action_activate()
            except Exception as exc:  # noqa: BLE001 — логваме и продължаваме
                _logger.warning(
                    "Автоматичното активиране на ДС %s пропадна: %s",
                    amendment.amendment_number, exc)
                amendment.message_post(body=_(
                    "Automatic activation failed: %s. The amendment stays "
                    "approved and needs manual review.", exc))

    @api.model
    def cron_expire_temporary_amendments(self):
        """Expire temporary amendments past their end date."""
        today = fields.Date.today()
        expired = self.search([
            ('state', '=', 'active'),
            ('is_temporary', '=', True),
            ('date_end', '<=', today),
        ])
        for rec in expired:
            rec.state = 'expired'
            if rec.is_temporary_assignment:
                revert = {}
                if rec.old_position_id:
                    revert['l10n_bg_qualification_group'] = rec.old_position_id.id
                if rec.old_work_location:
                    revert['work_location'] = rec.old_work_location
                if rec.old_economic_activity_id:
                    revert['l10n_bg_economic_activity_id'] = rec.old_economic_activity_id.id
                if revert:
                    rec.version_id.write(revert)

    def get_amendment_summary(self):
        """Human-readable summary of changes."""
        self.ensure_one()
        changes = []
        if self.old_wage and self.new_wage:
            changes.append(_('Wage: %.2f → %.2f') % (self.old_wage, self.new_wage))
        if self.old_position_id and self.new_position_id:
            changes.append(_('Position: %s → %s') % (
                self.old_position_id.name, self.new_position_id.name))
        if self.old_work_location and self.new_work_location:
            changes.append(_('Location: %s → %s') % (
                self.old_work_location, self.new_work_location))
        if self.old_working_time_type and self.new_working_time_type:
            changes.append(_('Working Time: %s → %s') % (
                self.old_working_time_type, self.new_working_time_type))
        if self.old_leave_days and self.new_leave_days:
            changes.append(_('Leave Days: %d → %d') % (
                self.old_leave_days, self.new_leave_days))
        return '\n'.join(changes)

    # =========================================================================
    # ONCHANGE
    # =========================================================================

    def _snapshot_old_values(self):
        """Текущите стойности на свързаната версия като vals за old_* полетата.

        Ползва се и от onchange-а (UI), и от одобрението (импорт/RPC) —
        иначе историята на ДС-то остава без „предишна стойност", а точно
        тя се печата в бланката."""
        self.ensure_one()
        v = self.version_id
        if not v:
            return {}
        return {
            'old_wage': v.wage,
            'old_position_id': v.l10n_bg_qualification_group.id,
            'old_economic_activity_id': v.l10n_bg_economic_activity_id.id,
            'old_working_time_type': v.l10n_bg_working_time_type,
            'old_daily_hours': v.l10n_bg_daily_hours,
            'old_weekly_hours': (v.l10n_bg_weekly_hours
                                 if 'l10n_bg_weekly_hours' in v._fields else 40.0),
            'old_work_location': v.work_location or '',
            'old_leave_days': v.l10n_bg_total_leave_days,
        }

    @api.onchange('version_id')
    def _onchange_version_id(self):
        """Load current values from the linked version."""
        if self.version_id:
            for field_name, value in self._snapshot_old_values().items():
                self[field_name] = value

    @api.onchange('amendment_type')
    def _onchange_amendment_type(self):
        if self.amendment_type == 'temporary_assignment':
            self.is_temporary = True
            self.is_temporary_assignment = True
        else:
            self.is_temporary_assignment = False

    @api.onchange('is_temporary')
    def _onchange_is_temporary(self):
        if not self.is_temporary:
            self.date_end = False
