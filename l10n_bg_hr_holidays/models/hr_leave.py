# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HRLeave(models.Model):
    _inherit = 'hr.leave'

    # Нови полета за функционалността
    l10n_bg_paid_days_unpaid_leave = fields.Float(
        string='Paid Days',
        related='work_entry_type_id.l10n_bg_paid_days_unpaid_leave',
        store=True,
        help='Number of days to be paid when the leave type is unpaid. '
             'These days will be deducted from the total unpaid days.',
        digits=(16, 1)  # Позволява 1 знак след запетаята за половин дни
    )

    l10n_bg_effective_unpaid_days = fields.Float(
        string='Effective Unpaid Days',
        compute='_compute_l10n_bg_effective_unpaid_days',
        store=True,
        digits=(16, 1),
        help='Total unpaid days minus the paid days (for unpaid leave types only)'
    )

    # Показва дали полетата трябва да са видими
    l10n_bg_show_paid_days_fields = fields.Boolean(
        string='Show Paid Days Fields',
        compute='_compute_show_paid_days_fields',
        help='Technical field to control visibility of paid days fields'
    )

    l10n_bg_leave_reason_id = fields.Many2one(
        related='work_entry_type_id.l10n_bg_leave_reason_id',
        store=True,
    )

    @api.depends('work_entry_type_id', 'work_entry_type_id.l10n_bg_allow_paid_days')
    def _compute_show_paid_days_fields(self):
        """Определя дали да показва полетата за платени дни"""
        for leave in self:
            leave.l10n_bg_show_paid_days_fields = (
                leave.work_entry_type_id and leave.work_entry_type_id.l10n_bg_allow_paid_days
            )

    @api.depends('number_of_days', 'l10n_bg_paid_days_unpaid_leave', 'work_entry_type_id', 'work_entry_type_id.l10n_bg_allow_paid_days')
    def _compute_l10n_bg_effective_unpaid_days(self):
        """Изчислява действителните неплатени дни след приспадане на платените"""
        for leave in self:
            if leave.work_entry_type_id and leave.work_entry_type_id.l10n_bg_allow_paid_days:
                leave.l10n_bg_effective_unpaid_days = max(0.0, leave.number_of_days - leave.l10n_bg_paid_days_unpaid_leave)
            else:
                leave.l10n_bg_effective_unpaid_days = 0.0

    @api.constrains('l10n_bg_paid_days_unpaid_leave', 'number_of_days', 'work_entry_type_id')
    def _check_l10n_bg_paid_days_unpaid_leave(self):
        """Валидира че платените дни не превишават общия брой дни"""
        for leave in self:
            if leave.work_entry_type_id and leave.work_entry_type_id.l10n_bg_allow_paid_days:
                if leave.l10n_bg_paid_days_unpaid_leave < 0:
                    raise ValidationError(
                        _('Paid days cannot be negative for leave request "%s".') % leave.name
                    )

    @api.constrains("number_of_days", "work_entry_type_id",
                    "employee_id", "request_date_from", "state")
    def _check_l10n_bg_max_days(self):
        """Валидира БГ-законовите лимити на отпуска.

        Два независими лимита (виж hr.work.entry.type):
        - l10n_bg_max_days_per_year — годишен таван (по календарна година)
        - l10n_bg_max_days_total — общ таван (lifetime / per event)

        Refuse/cancel заявки се изключват от агрегата.
        Стойност 0 = няма лимит → constraint пропуска.
        При нарушение показваме legal_reference към user-а.
        """
        for leave in self:
            ltype = leave.work_entry_type_id
            if not ltype:
                continue
            if leave.state in ("refuse", "cancel"):
                continue
            year_cap = ltype.l10n_bg_max_days_per_year or 0
            total_cap = ltype.l10n_bg_max_days_total or 0
            if not year_cap and not total_cap:
                continue
            ref = (
                _(" (Legal reference: %s)") % ltype.l10n_bg_legal_reference
                if ltype.l10n_bg_legal_reference else ""
            )

            if year_cap and leave.request_date_from:
                year_start = leave.request_date_from.replace(month=1, day=1)
                year_end = leave.request_date_from.replace(month=12, day=31)
                yearly_used = sum(self.search([
                    ("employee_id", "=", leave.employee_id.id),
                    ("work_entry_type_id", "=", ltype.id),
                    ("state", "in", ("confirm", "validate1", "validate")),
                    ("request_date_from", ">=", year_start),
                    ("request_date_from", "<=", year_end),
                    ("id", "!=", leave.id),
                ]).mapped("number_of_days") or [0.0])
                if yearly_used + (leave.number_of_days or 0.0) > year_cap:
                    raise ValidationError(_(
                        "Annual leave cap exceeded for leave type '%(type)s'. "
                        "Allowed: %(cap)d days/year; already used: "
                        "%(used).1f days; this request: %(req).1f days "
                        "(year of %(year)d).%(ref)s",
                        type=ltype.display_name,
                        cap=year_cap,
                        used=yearly_used,
                        req=leave.number_of_days or 0.0,
                        year=leave.request_date_from.year,
                        ref=ref,
                    ))

            if total_cap:
                total_used = sum(self.search([
                    ("employee_id", "=", leave.employee_id.id),
                    ("work_entry_type_id", "=", ltype.id),
                    ("state", "in", ("confirm", "validate1", "validate")),
                    ("id", "!=", leave.id),
                ]).mapped("number_of_days") or [0.0])
                if total_used + (leave.number_of_days or 0.0) > total_cap:
                    raise ValidationError(_(
                        "Total leave cap exceeded for leave type '%(type)s'. "
                        "Allowed: %(cap)d days total; already used: "
                        "%(used).1f days; this request: %(req).1f days."
                        "%(ref)s",
                        type=ltype.display_name,
                        cap=total_cap,
                        used=total_used,
                        req=leave.number_of_days or 0.0,
                        ref=ref,
                    ))

    @api.onchange('work_entry_type_id')
    def _onchange_work_entry_type_id_paid_days(self):
        """Нулира платените дни когато се промени типа отпуска"""
        if self.work_entry_type_id and not self.work_entry_type_id.l10n_bg_allow_paid_days:
            self.l10n_bg_paid_days_unpaid_leave = 0.0

    @api.onchange('l10n_bg_paid_days_unpaid_leave')
    def _onchange_l10n_bg_paid_days_unpaid_leave(self):
        """Предупреждава потребителя ако платените дни са повече от общия брой"""
        if (self.l10n_bg_paid_days_unpaid_leave and self.number_of_days and
            self.l10n_bg_paid_days_unpaid_leave != self.work_entry_type_id.l10n_bg_paid_days_unpaid_leave):
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _('Paid days (%.1f) exceed definned leave days (%.1f). '
                                 'Please adjust the values.') %
                               (self.l10n_bg_paid_days_unpaid_leave, self.work_entry_type_id.l10n_bg_paid_days_unpaid_leave)
                }
            }

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        # Odoo 19: BaseModel.name_search преименува args → domain.
        domain = domain or []
        extra_domain = []
        if name:
            extra_domain = ['|', ('code', operator, name), ('name', operator, name)]
        return super().name_search(
            name=name, domain=extra_domain + domain,
            operator=operator, limit=limit,
        )
