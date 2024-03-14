#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


def get_l10n_bg_applicability():
    return [
        ('declaration', _('Declaration')),
        ('purchase', _('Purchase report')),
        ('sale', _('Sale report')),
        ('vies', _('VIES Report'))
    ]


class AccountAccountTag(models.Model):
    _inherit = 'account.account.tag'

    description = fields.Text('Description', translate=True)
    l10n_bg_applicability = fields.Selection(selection=get_l10n_bg_applicability(), string='Use for')
