# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    l10n_bg_unpaid_type_id = fields.Many2one(
        'hr.work.entry.type',
        string='Unpaid Type',
        domain=[('is_leave', '=', True)],
        help='Work entry type which is considered unpaid for this type.',
        ondelete='set null',
    )
    l10n_bg_paid_days_unpaid_leave = fields.Float(
        string='Paid Days',
        compute='_compute_paid_days_unpaid_leave',
        help='Number of days to be paid when the leave type is unpaid. '
             'These days will be deducted from the total unpaid days.',
        digits=(16, 1)
    )

    @api.depends('leave_type_ids.l10n_bg_paid_days_unpaid_leave')
    def _compute_paid_days_unpaid_leave(self):
        for record in self:
            record.l10n_bg_paid_days_unpaid_leave = sum(record.leave_type_ids.mapped('l10n_bg_paid_days_unpaid_leave') or [0.0])

    @api.onchange('is_leave')
    def onchange_is_leave(self):
        if not self.is_leave and self.l10n_bg_unpaid_type_id:
            self.l10n_bg_unpaid_type_id = False
