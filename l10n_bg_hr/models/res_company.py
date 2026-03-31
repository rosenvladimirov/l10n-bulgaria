from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_bg_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='Economic Activity (KID)',
        help='Default economic activity code (KID 2008) for this company',
    )
