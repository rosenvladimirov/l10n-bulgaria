#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    purchase_type_vat = fields.Selection(selection=lambda self: self.env['account.move']._get_type_vat(),
                                         string="Type of numbering",
                                         default='standard')
    sale_type_vat = fields.Selection(selection=lambda self: self.env['account.move']._get_type_vat(),
                                     string="Type of numbering",
                                     default='standard')

    purchase_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_type_vat(),
                                         string="Vat type doc for purchase")
    sale_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_type_vat(),
                                     string="Vat type doc for sale")

    purchase_refund_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_type_vat(),
                                                string="Vat type doc for purchase refund")
    sale_refund_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_type_vat(),
                                            string="Vat type doc for sale refund")

    purchase_dn_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_type_vat(),
                                            string="Vat type doc for purchase debit note")
    sale_dn_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_type_vat(),
                                        string="Vat type doc for sale debit note")
