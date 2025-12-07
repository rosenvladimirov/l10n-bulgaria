
# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Extension of res.partner to add Bulgarian company registry integration"""
    _inherit = 'res.partner'

    # Bulgarian company fields (all prefixed with l10n_bg for consistency)
    l10n_bg_legal_form = fields.Char(
        string='Legal Form (Bulgarian)',
        help='Bulgarian legal form (ООД, ЕООД, АД, etc.)'
    )
    l10n_bg_registration_date = fields.Date(
        string='Registration Date',
        help='Date of company registration in Bulgarian Trade Register'
    )
    l10n_bg_registration_court = fields.Char(
        string='Registration Court',
        help='Court where company is registered'
    )
    l10n_bg_activity_code = fields.Char(
        string='Activity Code (NACE)',
        help='Main economic activity code'
    )
    l10n_bg_activity_description = fields.Text(
        string='Activity Description'
    )

    def action_fetch_from_registry(self):
        """
        Open wizard to fetch and populate company data from Bulgarian Company Registry
        """
        self.ensure_one()

        if not self.vat or not self.vat.upper().startswith('BG'):
            raise UserError(_('Моля въведете валиден български ДДС номер (започва с BG)'))

        if self.l10n_bg_uic_type != 'bg_uic':
            raise UserError(_('Този метод работи само за български ЕИК номера'))

        # Extract EIK from VAT
        eik = self.vat.upper().replace('BG', '').strip()

        # Open wizard
        return {
            'name': _('Данни от търговски регистър'),
            'type': 'ir.actions.act_window',
            'res_model': 'bg.company.search.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_eik': eik,
            }
        }
