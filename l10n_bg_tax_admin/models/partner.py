#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    def _get_default_get(self, mode=0):
        company_id = self.env.company
        value = ''
        out_type_fp = self.env.ref(f'l10n_bg.{company_id}_fiscal_position_template_out_eu', raise_if_not_found=False).id
        in_type_fp = self.env.ref(f'l10n_bg.{company_id}_fiscal_position_template_in_eu', raise_if_not_found=False).id
        standard_type_fp = self.env.ref(f'l10n_bg.{company_id}_fiscal_position_template_dom',
                                        raise_if_not_found=False).id
        if self.id == out_type_fp:
            if mode == 1:
                value = 'out_customs'
            elif mode == 2:
                value = 'in_customs'
            elif mode in [3, 4, 5, 6, 7, 8]:
                value = '07'

        if self.id == in_type_fp:
            if mode == 1:
                value = 'standard'
            elif mode == 2:
                value = '117_protocol'
            elif mode in [3, 5, 7]:
                value = '09'
            elif mode in [4, 6, 8]:
                value = '01'

        if self.id == standard_type_fp:
            if mode == 1:
                value = 'standard'
            elif mode == 2:
                value = 'standard'
            elif mode == [3, 4]:
                value = '01'
            elif mode in [5, 6]:
                value = '03'
            elif mode in [7, 8]:
                value = '02'
        return value

    purchase_type_vat = fields.Selection(selection=lambda self: self.env['account.move']._get_type_vat(),
                                         string="Type of numbering",
                                         default=lambda self: self._get_default_get(mode=2))
    sale_type_vat = fields.Selection(selection=lambda self: self.env['account.move']._get_type_vat(),
                                     string="Type of numbering",
                                     default=lambda self: self._get_default_get(mode=1))

    purchase_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_doc_type(),
                                         string="Vat type doc for purchase",
                                         default=lambda self: self._get_default_get(mode=3)
                                         )
    sale_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_doc_type(),
                                     string="Vat type doc for sale",
                                     default=lambda self: self._get_default_get(mode=4)
                                     )

    purchase_refund_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_doc_type(),
                                                string="Vat type doc for purchase refund",
                                                default=lambda self: self._get_default_get(mode=5)
                                                )
    sale_refund_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_doc_type(),
                                            string="Vat type doc for sale refund",
                                            default=lambda self: self._get_default_get(mode=6)
                                            )

    purchase_dn_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_doc_type(),
                                            string="Vat type doc for purchase debit note",
                                            default=lambda self: self._get_default_get(mode=7)
                                            )
    sale_dn_doc_type = fields.Selection(selection=lambda self: self.env['account.move']._get_doc_type(),
                                        string="Vat type doc for sale debit note",
                                        default=lambda self: self._get_default_get(mode=8)
                                        )
    purchase_fp_replace_id = fields.Many2one('account.fiscal.position',
                                             'Purchase replace with',
                                             help='Replace fiscal position if create account entry base '
                                                  'on invoice case import and export outside of EU')
    sale_fp_replace_id = fields.Many2one('account.fiscal.position',
                                         'Sale replace with',
                                         help='Replace fiscal position if create account entry base '
                                              'on invoice case import and export outside of EU')
