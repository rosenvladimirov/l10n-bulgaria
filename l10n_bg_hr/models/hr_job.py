from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = 'hr.job'

    l10n_bg_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='Economic Activity (KID)',
        default=lambda self: self.env.company.l10n_bg_economic_activity_id,
        help='Economic activity code (KID 2008) for this position',
    )

    # Related fields from NCOP for summary display
    l10n_bg_qualification_group = fields.Selection(
        related='l10n_bg_ncop_position_id.qualification_group',
        string='Qualification Group', readonly=True,
    )
    l10n_bg_education_level = fields.Selection(
        related='l10n_bg_ncop_position_id.education_level',
        string='Education Level', readonly=True,
    )
    l10n_bg_ncop_code = fields.Char(
        related='l10n_bg_ncop_position_id.code',
        string='NKPD Code', readonly=True,
    )
