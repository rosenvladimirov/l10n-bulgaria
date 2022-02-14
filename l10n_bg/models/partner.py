# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    def _selection_type_docs(self, type_doc=False):
        if type_doc == 'out' or self._context.get('force_type_docs', '') == 'out':
            return [
                ('standart', 'Standard for invoices'),
                ('ticket', 'B2C Invoices'),
                ('ictcustoms', 'Intra community transits (Vendor customs)'),
                ('trpprotocol', 'Tri party EU deals')
            ]
        elif type_doc == 'in' or self._context.get('force_type_docs', '') == 'in':
            return [
                ('standart', 'Standard for invoices'),
                ('customs', 'Customs declaration'),
                ('protocol', 'Swap incoming invoices with a protocol'),
            ]
        return [
            ('standart', 'Standart for invoices'),
            ('ticket', 'B2C Invoices'),
            ('customs', 'Customs declaration'),
            ('ictcustoms', 'Intra community transits (Vendor customs)'),
            ('protocol', 'Swap incoming invoices with a protocol'),
            ('trpprotocol', 'Tri party EU deals')
        ]

    type_docs = fields.Selection(selection=lambda self: self.env['account.fiscal.position']._selection_type_docs(),
                                 string="Types of docs", default='standart', help='Technical field for all cases')
    purchase_type_docs = fields.Selection(
        selection=lambda self: self.env['account.fiscal.position']._selection_type_docs('in'),
        string="Types of docs fo sales", default='standart', help='Technical field for purchase cases')
    sale_type_docs = fields.Selection(
        selection=lambda self: self.env['account.fiscal.position']._selection_type_docs('out'),
        string="Types of docs for purchase", default='standart', help='Technical field for purchase cases')
