# -*- coding: utf-8 -*-
# Изнесено от l10n_bg_hr_payroll (18.0.18.11.0) без промяна на дефиницията.

from odoo import models, fields


class HrContractType(models.Model):
    _inherit = 'hr.contract.type'

    l10n_bg_contract_duration_type = fields.Selection([
        ('indefinite', 'Indefinite Period'),
        ('fixed_term', 'Fixed Term'),
        ('specific_work', 'Until Completion of Specific Work'),
        ('replacement', 'Replacement')
    ], string='BG Contract Duration Type',
        default='indefinite',
        help='Duration type as required by Art. 68 of Bulgarian Labor Code')
