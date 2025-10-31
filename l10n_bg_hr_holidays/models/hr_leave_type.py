# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HRLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    l10n_bg_code = fields.Char(
        string='Code',
        help='Internal code for the leave type (e.g., KT155, NSSI01)',
        copy=False,
        index=True,
    )
    l10n_bg_allow_paid_days = fields.Boolean(
        string='Allow Paid Days',
        compute='_compute_l10n_bg_allow_paid_days',
        store=True,
        help='Technical field to determine if paid days can be specified for this leave type'
    )
    l10n_bg_paid_days_unpaid_leave = fields.Float(
        string='Paid Days',
        default=0.0,
        help='Number of days to be paid when the leave type is unpaid. '
             'These days will be deducted from the total unpaid days.',
        digits=(16, 1)
    )
    l10n_bg_leave_reason_id = fields.Many2one(
        'nssi.leave.reason',
        string='Leave Reason'
    )

    @api.depends('time_type')
    def _compute_l10n_bg_allow_paid_days(self):
        """Compute whether paid days are allowed for this leave type"""
        for leave_type in self:
            leave_type.l10n_bg_allow_paid_days = leave_type.time_type == 'leave'

    @api.depends('l10n_bg_code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.l10n_bg_code and f'[{record.l10n_bg_code}] '}{record.name}"
