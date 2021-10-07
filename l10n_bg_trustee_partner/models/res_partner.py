# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = ['res.partner']
    _name = 'res.partner'

    property_account_trustee_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Тrustee",
        domain="[('internal_type', '=', 'liquidity'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the liquidity account for the current Тrustee partner",
        )
