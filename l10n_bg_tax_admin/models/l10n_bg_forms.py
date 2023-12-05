#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class TAXForms(models.Model):
    _inherit = 'tax.forms'

    account_forms = fields.Selection(selection_add=[
        ('vat_purchase', _('VAT Purchase journal')),
        ('vat_sale', _('VAT Sale journal')),
        ('vat_vies', _('VIES Declaration')),
    ])
