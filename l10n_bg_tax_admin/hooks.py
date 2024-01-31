#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools.translate import load_language

from odoo import SUPERUSER_ID, api


def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    #  mark fiscal position to update
    fiscal_position = env['ir.model.data'].search([
        ('module', '=', 'l10n_bg'),
        ('model', '=', 'account.fiscal.position.template')
    ])
    taxes = env['ir.model.data'].search([
        ('module', '=', 'l10n_bg'),
        ('model', '=', 'account.tax.template')
    ])
    for fp in fiscal_position + taxes:
        fp.update({
            'noupdate': False,
        })
