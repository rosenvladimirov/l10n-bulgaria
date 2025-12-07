# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_round


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    l10n_bg_paid_days_unpaid_leave = fields.Float(
        string='Paid Days',
        compute='_compute_l10n_bg_effective_unpaid_days',
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

    l10n_bg_number_of_days_original = fields.Float(
        string='Original Days',
        compute='_compute_l10n_bg_effective_unpaid_days',
        store=True,
        help='Technical field to save original number_of_days',
        digits=(16, 1)  # Позволява 1 знак след запетаята за половин дни
    )

    l10n_bg_number_of_hours_original = fields.Float(
        string='Original Hours',
        compute='_compute_l10n_bg_effective_unpaid_days',
        store=True,
        help='Technical field to save original number_of_hours',
        digits=(16, 1)  # Позволява 1 знак след запетаята за половин дни
    )
    l10n_bg_manual_edit = fields.Boolean(
        string='Manual Edit',
        help='Flag to indicate if the number of days was manually edited'
    )

    @api.depends('number_of_days', 'number_of_hours', 'work_entry_type_id')
    def _compute_l10n_bg_effective_unpaid_days(self):
        for record in self.filtered(lambda x: x.l10n_bg_manual_edit):
            if record.work_entry_type_id.is_leave:
                number_of_days = record.number_of_days or 0.0
                number_of_hours = record.number_of_hours or 0.0
                daily_hours = number_of_hours / number_of_days
                record.l10n_bg_number_of_days_original = number_of_days
                record.l10n_bg_number_of_hours_original = number_of_hours
                l10n_bg_paid_days_unpaid_leave = 0.0
                for leave_type_id in record.work_entry_type_id.mapped('leave_type_ids'):
                    l10n_bg_paid_days_unpaid_leave += leave_type_id.l10n_bg_paid_days_unpaid_leave
                record.l10n_bg_paid_days_unpaid_leave = float_round(l10n_bg_paid_days_unpaid_leave, 2)
                record.l10n_bg_effective_unpaid_days = max(0.0, record.number_of_days - l10n_bg_paid_days_unpaid_leave)
                record.number_of_days = l10n_bg_paid_days_unpaid_leave
                record.number_of_hours = l10n_bg_paid_days_unpaid_leave * daily_hours
            else:
                record.l10n_bg_number_of_days_original = record.number_of_days
                record.l10n_bg_number_of_hours_original = record.number_of_hours
                record.l10n_bg_effective_unpaid_days = 0.0
                record.l10n_bg_paid_days_unpaid_leave = record.number_of_days

    @api.onchange('number_of_days', 'number_of_hours')
    def onchange_l10n_bg_manual_edit(self):
        if self.work_entry_type_id.is_leave and self._context.get('manual_edit'):
            self.l10n_bg_manual_edit = self._context['manual_edit']
