# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrContractType(models.Model):
    _inherit = 'hr.contract.type'

    l10n_bg_contract_duration_type = fields.Selection([
        ('indefinite', 'Indefinite Period'),
        ('fixed_term', 'Fixed Term'),
        ('specific_work', 'Until Completion of Specific Work'),
        ('replacement', 'Replacement'),
        # 172197 т. 4: чл. 68, ал. 1, т. 4 КТ — няма календарен срок,
        # свършва с постъпването на спечелилия конкурса (основание 008).
        ('competition', 'Until Filled by Competition'),
    ], string='BG Contract Duration Type',
        default='indefinite',
        help='Duration type as required by Art. 68 of Bulgarian Labor Code')

    # DEF-209 т. 2 (Пламена, 15.10.2026): т. 12 на Приложение № 1 към НВРЗ.
    # 007 („с изпитателен срок по чл. 70“) не е основание в наредбата —
    # изпитателният срок е клауза; 018–021 са основания за ИЗМЕНЕНИЕ (ДС).
    # Остават в данните заради заварените версии, но не се предлагат при
    # назначаване.
    l10n_bg_hiring_allowed = fields.Boolean(
        string='Allowed on Hiring',
        default=True,
        help='Offered as the contract type of an employment. Grounds that '
             'exist only for amendments (Annex 1, item 12, codes 018–021) or '
             'are not grounds at all are kept for existing records but hidden.',
    )
