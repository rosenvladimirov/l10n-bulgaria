# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    type_docs = fields.Selection([
        ('standart', 'Standart for invoices'),
        ('ticket', 'B2C Invoices'),
        ('customs', 'Customs declaration'),
        ('ictcustoms', 'Intra community transits (Vendor customs)'),
        ('protocol', 'Swap incoming invoices with a protocol'),
        ('trpprotocol', 'Tri party EU deals')
    ], string="Types of docs", default='standart')
