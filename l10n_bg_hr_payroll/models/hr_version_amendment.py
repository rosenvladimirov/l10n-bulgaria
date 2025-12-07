# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrContractAmendment(models.Model):
    _inherit = 'l10n_bg.hr.version.amendment'

    l10n_bg_nap_export_history_ids = fields.One2many(
        'l10n_bg.nap.export.history',
        'contract_amendment_id',
        string='NAP Export History'
    )
