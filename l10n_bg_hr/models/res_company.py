# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # КИД на фирмата по подразбиране — от него длъжността взима своя КИД,
    # когато не е посочен изрично (пренесено от 19).
    l10n_bg_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='Economic Activity (KID)',
        help='Default economic activity code (KID 2008) for this company',
    )
