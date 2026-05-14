# -*- coding: utf-8 -*-
from odoo import fields, models


class ResBank(models.Model):
    _inherit = 'res.bank'

    l10n_bg_nap_approved = fields.Boolean(
        string='NAP-Approved',
        default=False,
        help='Mark banks that are on the National Revenue Agency''s list of '
             'institutions approved for payment of budget receivables '
             '(tax, social contributions, customs). Used to filter the '
             'bank-account picker in payment-order wizards so a treasurer '
             'only sees institutions that can process government payments.',
    )
