# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HRLeave(models.Model):
    _inherit = 'hr.leave'

    def action_approve(self, check_state=True):
        res = super().action_approve(check_state=check_state)
        for leave in self.filtered(lambda x: x.state == 'validate1' and x.l10n_bg_leave_reason_id):
            version_id = leave.employee_id.version_id
            if version_id and not version_id.l10n_bg_nssi_certificate_ids.filtered(lambda c: c.leave_sick_id == leave):
                version_id.l10n_bg_nssi_certificate_ids |= leave
        return res
