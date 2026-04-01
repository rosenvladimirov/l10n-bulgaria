# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_bg_amendment_ids = fields.One2many(
        'l10n_bg.hr.version.amendment',
        'employee_id',
        string='Contract Amendments',
    )

    l10n_bg_amendment_count = fields.Integer(
        string='Amendment Count',
        compute='_compute_amendment_count',
    )

    l10n_bg_last_amendment_date = fields.Date(
        string='Last Amendment Date',
        compute='_compute_last_amendment',
    )

    l10n_bg_last_amendment_summary = fields.Char(
        string='Last Amendment Changes',
        compute='_compute_last_amendment',
    )

    @api.depends('l10n_bg_amendment_ids')
    def _compute_amendment_count(self):
        for employee in self:
            employee.l10n_bg_amendment_count = len(employee.l10n_bg_amendment_ids)

    @api.depends('l10n_bg_amendment_ids.state', 'l10n_bg_amendment_ids.date_effective')
    def _compute_last_amendment(self):
        for employee in self:
            last = employee.l10n_bg_amendment_ids.filtered(
                lambda a: a.state in ('active', 'approved', 'to_approve')
            ).sorted('date_effective', reverse=True)[:1]
            employee.l10n_bg_last_amendment_date = last.date_effective if last else False
            employee.l10n_bg_last_amendment_summary = last.get_amendment_summary() if last else ''
