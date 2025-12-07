# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, Command, fields, models, _

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_worked_day_lines_values(self, domain=None):
        self.ensure_one()
        new_res = []
        res = super()._get_worked_day_lines_values(domain=domain)
        for line in res:
            work_entry_type = self.env['hr.work.entry.type'].browse(line['work_entry_type_id']) if line.get('work_entry_type_id') else False
            number_of_days = line.get('number_of_days') or 0.0
            number_of_hours = line.get('number_of_hours') or 0.0
            insurance_rates = self.env['hr.rule.parameter']._get_parameter_from_code(
                'BG_INSURANCE_RATE',
                self.date_from,
                raise_if_not_found=True
            ) or 0.70
            insurance_months = self.env['hr.rule.parameter']._get_parameter_from_code(
                'BG_INSURANCE_MONTHS',
                self.date_from,
                raise_if_not_found=True
            ) or 6.0

            if (work_entry_type and work_entry_type.is_leave
                and work_entry_type.l10n_bg_unpaid_type_id):
                line['l10n_bg_number_of_days_original'] = number_of_days
                line['l10n_bg_number_of_hours_original'] = number_of_hours
                daily_hours = number_of_hours / number_of_days
                l10n_bg_paid_days_unpaid_leave = 0.0
                if self.version_id.l10n_bg_insurance_months >= insurance_months:
                    unpaid_line_ids = work_entry_type.mapped('leave_type_ids')
                    for unpaid_line in unpaid_line_ids:
                        l10n_bg_paid_days_unpaid_leave += unpaid_line.l10n_bg_paid_days_unpaid_leave

                if work_entry_type.l10n_bg_unpaid_type_id.id != line['work_entry_type_id']:
                    attendance_line = {
                        'sequence': work_entry_type.l10n_bg_unpaid_type_id.sequence,
                        'work_entry_type_id': work_entry_type.l10n_bg_unpaid_type_id.id,
                        'number_of_days': number_of_days - l10n_bg_paid_days_unpaid_leave,
                        'number_of_hours': number_of_hours - l10n_bg_paid_days_unpaid_leave * daily_hours
                    }
                    new_res.append(attendance_line)
                    line['number_of_days'] = l10n_bg_paid_days_unpaid_leave
                    line['number_of_hours'] = l10n_bg_paid_days_unpaid_leave * daily_hours
        return res + new_res
