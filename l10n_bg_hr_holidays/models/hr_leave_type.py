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
    l10n_bg_doo_treatment = fields.Selection([
        ('normal', 'Normal — employer DOO/ZO/UPF on wage'),
        ('nssi_maternity', 'NSSI-funded maternity (чл. 163, 164, 163-10, 166 КТ)'),
        ('nssi_sick', 'NSSI-funded sick leave (after 3 employer-paid days, чл. 162 КТ)'),
        ('unpaid_no_doo', 'Unpaid > 30 days/year — excluded from DOO base'),
    ],
        string='DOO Treatment',
        default='normal',
        help='How this leave type interacts with social-security contributions. '
             '`normal` — employer pays DOO/ZO/UPF based on wage as usual. '
             '`nssi_maternity` — NSSI pays the benefit AND funds the social-security '
             'contributions; employer DOO base excludes these days (чл. 50 КСО). '
             '`nssi_sick` — first 3 days employer-paid (70%), remainder NSSI-funded. '
             '`unpaid_no_doo` — unpaid leave above 30 days/year per чл. 160 ал. 1 КТ '
             '— excluded from DOO base entirely.'
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
