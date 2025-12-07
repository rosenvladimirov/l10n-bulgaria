from odoo import models, fields, api, _


class HrLeaveNSSICertificate(models.Model):
    _name = 'hr.leave.nssi.certificate'
    _description = 'NOI Application – Appendix 9'
    _order = 'create_date desc'

    version_id = fields.Many2one(
        'hr.version', string='Contract', required=True, ondelete='cascade')
    leave_sick_id = fields.Many2one(
        'hr.leave',
        'Sick Leave'
    )
    leave_sick_domain = fields.Binary(
        compute='_compute_leave_sick_domain'
    )

    # --- Identification ---
    sick_leave_number = fields.Char(string='Hospital Sheet No.', required=True)
    l10n_bg_egn = fields.Char(
        related='version_id.employee_id.identification_id',
        string='EGN',
        readonly=True,
    )
    l10n_bg_uic = fields.Char(
        related='version_id.company_id.l10n_bg_uic',
        readonly=True
    )

    # --- Period & Reason ---
    date_from = fields.Datetime(related='leave_sick_id.date_from')
    date_to = fields.Datetime(related='leave_sick_id.date_to')
    leave_reason_code = fields.Char(related='leave_sick_id.name')

    # --- Income & Insurance ---
    income_1 = fields.Float(string='Income -1')
    income_2 = fields.Float(string='Income -2')
    income_3 = fields.Float(string='Income -3')
    income_4 = fields.Float(string='Income -4')
    income_5 = fields.Float(string='Income -5')
    income_6 = fields.Float(string='Income -6')
    insured_months = fields.Float(related='version_id.l10n_bg_insurance_months')
    insured_days = fields.Float(related='leave_sick_id.l10n_bg_paid_days_unpaid_leave')
    worked_days_period = fields.Integer(string='Worked Days in Period')

    # --- Payment data ---
    bank_account_id = fields.Many2one(related='version_id.employee_id.bank_account_id')
    nssi_office_code = fields.Char(string='NSSI Office Code')

    # --- Misc ---
    representative_name = fields.Char(string='Representative')
    representative_position = fields.Char(string='Position')

    total_income = fields.Float(
        string='Total Income', compute='_compute_total_income', store=True)

    @api.depends('income_1', 'income_2', 'income_3', 'income_4', 'income_5', 'income_6')
    def _compute_total_income(self):
        for rec in self:
            rec.total_income = sum(
                [rec.income_1, rec.income_2, rec.income_3,
                 rec.income_4, rec.income_5, rec.income_6])

    @api.depends('version_id.employee_id')
    def _compute_leave_sick_domain(self):
        SickType = self.env['hr.leave.type']
        sick_types = SickType.search([('time_type', '=', 'leave')]).ids

        for rec in self:
            if not rec.version_id.employee_id or not sick_types:
                rec.leave_sick_domain = []  # empty domain
                continue

            # binary (prefix) syntax "AND AND …"
            rec.leave_sick_domain = [
                '&', '&',
                ('employee_id', '=', rec.version_id.employee_id.id),
                ('state', '=', 'validate'),
                ('holiday_status_id', 'in', sick_types),
            ]
