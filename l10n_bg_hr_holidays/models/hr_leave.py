# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HRLeave(models.Model):
    _inherit = 'hr.leave'

    code = fields.Char('Code')

    # Нови полета за функционалността
    l10n_bg_paid_days_unpaid_leave = fields.Float(
        string='Paid Days',
        related='holiday_status_id.l10n_bg_paid_days_unpaid_leave',
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
        related='holiday_status_id.l10n_bg_leave_reason_id',
        store=True,
    )

    @api.depends('code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.code and f'[{record.code}] '}{record.name}"

    @api.depends('holiday_status_id', 'holiday_status_id.l10n_bg_allow_paid_days')
    def _compute_show_paid_days_fields(self):
        """Определя дали да показва полетата за платени дни"""
        for leave in self:
            leave.l10n_bg_show_paid_days_fields = (
                leave.holiday_status_id and leave.holiday_status_id.l10n_bg_allow_paid_days
            )

    @api.depends('number_of_days', 'l10n_bg_paid_days_unpaid_leave', 'holiday_status_id', 'holiday_status_id.l10n_bg_allow_paid_days')
    def _compute_l10n_bg_effective_unpaid_days(self):
        """Изчислява действителните неплатени дни след приспадане на платените"""
        for leave in self:
            if leave.holiday_status_id and leave.holiday_status_id.l10n_bg_allow_paid_days:
                leave.l10n_bg_effective_unpaid_days = max(0.0, leave.number_of_days - leave.l10n_bg_paid_days_unpaid_leave)
            else:
                leave.l10n_bg_effective_unpaid_days = 0.0

    @api.constrains('l10n_bg_paid_days_unpaid_leave', 'number_of_days', 'holiday_status_id')
    def _check_l10n_bg_paid_days_unpaid_leave(self):
        """Валидира че платените дни не превишават общия брой дни"""
        for leave in self:
            if leave.holiday_status_id and leave.holiday_status_id.l10n_bg_allow_paid_days:
                if leave.l10n_bg_paid_days_unpaid_leave < 0:
                    raise ValidationError(
                        _('Paid days cannot be negative for leave request "%s".') % leave.name
                    )

    @api.onchange('holiday_status_id')
    def _onchange_holiday_status_id_paid_days(self):
        """Нулира платените дни когато се промени типа отпуска"""
        if self.holiday_status_id and not self.holiday_status_id.l10n_bg_allow_paid_days:
            self.l10n_bg_paid_days_unpaid_leave = 0.0

    @api.onchange('l10n_bg_paid_days_unpaid_leave')
    def _onchange_l10n_bg_paid_days_unpaid_leave(self):
        """Предупреждава потребителя ако платените дни са повече от общия брой"""
        if (self.l10n_bg_paid_days_unpaid_leave and self.number_of_days and
            self.l10n_bg_paid_days_unpaid_leave != self.holiday_status_id.l10n_bg_paid_days_unpaid_leave):
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _('Paid days (%.1f) exceed definned leave days (%.1f). '
                                 'Please adjust the values.') %
                               (self.l10n_bg_paid_days_unpaid_leave, self.holiday_status_id.l10n_bg_paid_days_unpaid_leave)
                }
            }
