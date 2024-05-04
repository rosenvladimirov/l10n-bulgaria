#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re

from odoo import api, fields, models, _, Command

_logger = logging.getLogger(__name__)


class AccountMoveBgCustoms(models.Model):
    _name = "account.move.bg.customs"
    _inherits = {'account.move': 'move_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _description = "Customs declarations"
    _order = "date_creation desc, name desc, id desc"
    _mail_post_access = 'read'
    _check_company_auto = True
    _sequence_field = 'customs_name'
    _sequence_date_field = 'customs_date'

    move_id = fields.Many2one('account.move', string='Account invoice', ondelete="cascade", required=True, index=True)
    date_creation = fields.Date('Created Date', required=True, default=fields.Date.today())
    customs_date = fields.Date("Date", copy=False, default=fields.Date.today())
    customs_name = fields.Char(
        string='Customs Number',
        copy=False,
        tracking=True,
        index='trigram',
    )
    l10n_bg_customs_invoice_ids = fields.Many2many('account.move',
                                                   'customs_invoices_rel',
                                                   'invoice_id',
                                                   'customs_id',
                                                   string='Used invoices in customs',
                                                   check_company=True,
                                                   copy=False,
                                                   readonly=True,
                                                   states={'draft': [('readonly', False)]},
                                                   )

    def _customs_aml(self, invoice_id, new_entry_id, map_id, partner_id):
        # Create new account moves
        partner_id = partner_id or self.partner_id
        partner_account_id = self.env['account.account']._get_most_frequent_account_for_partner(
            company_id=self.company_id.id,
            partner_id=partner_id.id,
            move_type=invoice_id.move_type,
        )
        partner_account_id = self.env['account.account'].browse(partner_account_id)
        base_lines = invoice_id.invoice_line_ids.filtered(lambda r: r.display_type == 'product')
        amount_currency_total = 0.0
        factor_percent = map_id.factor_percent == 0.0 and 100.0 or map_id.factor_percent
        for line in base_lines:
            amount_currency_total += line.amount_currency
        amount_currency_total *= factor_percent / 100
        account_id = map_id.account_id and map_id.account_id or partner_account_id
        tax_ids = account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == 'purchase')
        if not tax_ids:
            tax_ids = invoice_id.company_id.account_purchase_tax_id
        if tax_ids and new_entry_id.fiscal_position_id:
            tax_ids = new_entry_id.fiscal_position_id.map_tax(tax_ids)
        aml_vals_list = [Command.create({
            'display_type': 'product',
            'account_id': account_id.id,
            'partner_id': partner_id.id,
            'currency_id': invoice_id.currency_id.id,
            'amount_currency': amount_currency_total,
            'balance': amount_currency_total * invoice_id.l10n_bg_currency_rate,
            'tax_ids': [Command.set(tax_ids.ids)],
        })]
        return aml_vals_list

    def _customs_vals(self, move_id):
        return {
            'move_id': move_id.id,
            'customs_name': 'BG',
            'customs_date': move_id.invoice_date,
            'l10n_bg_customs_invoice_ids': [Command.set(move_id.ids)]
        }
