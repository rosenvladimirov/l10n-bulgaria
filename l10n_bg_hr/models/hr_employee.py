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

    @api.depends('l10n_bg_amendment_ids')
    def _compute_amendment_count(self):
        for employee in self:
            employee.l10n_bg_amendment_count = len(employee.l10n_bg_amendment_ids)
