# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # НКПД / КИД (related from current version)
    l10n_bg_qualification_group = fields.Many2one(
        related='version_id.l10n_bg_qualification_group',
        inherited=True,
        readonly=False,
        groups="hr.group_hr_user",
    )
    l10n_bg_economic_activity_id = fields.Many2one(
        related='version_id.l10n_bg_economic_activity_id',
        inherited=True,
        readonly=False,
        groups="hr.group_hr_user",
    )
    l10n_bg_economic_activity_code = fields.Char(
        related='version_id.l10n_bg_economic_activity_code',
        inherited=True,
        groups="hr.group_hr_user",
    )
    l10n_bg_workplace_code = fields.Char(
        related='version_id.l10n_bg_workplace_code',
        inherited=True,
        readonly=False,
        groups="hr.group_hr_user",
    )

    def action_refresh_nkpd_kid(self):
        """Refresh НКПД and КИД from current job position."""
        for employee in self:
            version = employee.version_id
            if not version:
                continue
            job = version.job_id
            if not job:
                continue
            vals = {}
            if job.l10n_bg_ncop_position_id:
                vals['l10n_bg_qualification_group'] = job.l10n_bg_ncop_position_id.id
            if job.l10n_bg_economic_activity_id:
                vals['l10n_bg_economic_activity_id'] = job.l10n_bg_economic_activity_id.id
            if vals:
                version.write(vals)

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
