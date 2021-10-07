# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class account_abstract_payment(models.AbstractModel):
    _inherit = "account.abstract.payment"

    partner_trustee_id = fields.Many2one('res.partner', string='Trustee Partner')


class account_payment(models.Model):
    _inherit = "account.payment"

    @api.onchange('journal_id')
    def _onchange_journal(self):
        res = super(account_payment, self)._onchange_journal()
        if self.journal_id:
            domain = (self.journal_id.default_debit_account_id and self.journal_id.default_debit_account_id.id or False,\
                      self.journal_id.default_credit_account_id and self.journal_id.default_credit_account_id.id or False)
            res.update({'domain': {'partner_trustee_id': [('property_account_trustee_id', 'in', domain)]}})
        #_logger.info("Jornal ___ %s" % res)
        return res

    def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id, invoice_id=False):
        res = super(account_payment, self)._get_shared_move_line_vals(debit, credit, amount_currency, move_id, invoice_id=invoice_id)
        if self.partner_trustee_id:
            #res['name'] = "**".join([res['name'], self.partner_trustee_id.display_name])
            res.update({'partner_id': self.partner_trustee_id.id})
        return res

    def _get_counterpart_move_line_vals(self, invoice=False):
        res = super(account_payment, self)._get_counterpart_move_line_vals(invoice=invoice)
        if self.partner_trustee_id:
            res['name'] = "**".join([res['name'], self.partner_trustee_id.display_name])
            res.update({'partner_id': self.payment_type in ('inbound', 'outbound') and self.env['res.partner']._find_accounting_partner(self.partner_id).id or False})
        return res
