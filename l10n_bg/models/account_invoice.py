# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from itertools import groupby

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from functools import partial
from odoo.tools.misc import formatLang
from odoo.tools import float_is_zero, float_compare, pycompat
from odoo.addons.account.models import account_invoice as accountinvoice
from odoo.addons.account.models.account_invoice import MAGIC_COLUMNS

import logging

_logger = logging.getLogger(__name__)

# mapping invoice type to debit note type
TYPE2DEBITNOTE = {
    'out_invoice': 'out_debitnote',  # Customer Debit Note
    'in_invoice': 'in_debitnote',  # Vendor Debit Note
    'out_debitnote': 'out_invoice',  # Customer Credit Note
    'in_debitnote': 'in_invoice',  # Vendor Credit Note
    'out_refund': 'out_refund',  # Customer Credit Note
    'in_refund': 'in_refund',  # Vendor Credit Note
}


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def _compute_amount(self):
        round_curr = self.currency_id.round
        round_curr_company = self.company_currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_tax = self.amount_tax_company = 0.0
        for line in self.tax_line_ids:
            if line.tax_id.tax_credit_payable not in ['taxadvpay', 'othertax']:
                self.amount_tax += round_curr(line.amount_total)
                if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
                    self.amount_tax_company += round_curr_company(line.amount_currency)

        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.with_context(
                {"lang": invoice.partner_id.lang}).amount_to_text(invoice.amount_total)

    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words", translate=True,
                                     store=True)
    amount_tax_company = fields.Monetary(string='Tax in Company Currency',
                                         store=True, readonly=True, compute='_compute_amount',
                                         currency_field="company_currency_id")
    invoice_number = fields.Char("Invoice number", index=True,
                                 readonly=True, states={'open': [('readonly', False)]}, copy=False)
    protocol_number = fields.Char("Protocol number", index=True,
                                  readonly=True, states={'open': [('readonly', False)]}, copy=False)
    ticket_number = fields.Char("Ticket number", index=True,
                                readonly=True, states={'open': [('readonly', False)]}, copy=False)
    customs_number = fields.Char("Customs number", index=True,
                                 readonly=True, states={'open': [('readonly', False)]}, copy=False)
    type_docs = fields.Selection(related="fiscal_position_id.type_docs", store=True)
    debitnote_invoice_id = fields.Many2one('account.invoice', string="Invoice for which this invoice is the debit note")
    debitnote_invoice_ids = fields.One2many('account.invoice', 'debitnote_invoice_id', string='Debit Notes',
                                            readonly=True)
    sub_type = fields.Selection([
        ('out_debitnote', _('Customer Debit note')),
        ('in_debitnote', _('Vendor Debit Note')),
        ('out_refund', _('Customer Credit Note')),
        ('in_refund', _('Vendor Credit Note')),
        ('out_invoice', _('Customer Invoice')),
        ('in_invoice', _('Vendor Bill')),
        ('nosubtype', _('Standart document'))
    ], readonly=True, index=True, change_default=True, default='nosubtype')
    eu_deals = fields.Boolean('The intra-Community supply tax is chargeable', default=True)
    doc_justification = fields.Boolean('Documentary justification', default=True)
    tax_type_deal = fields.Selection([
        ('auto', _('Automatic discovery')),
        ('standard', _('Product direct selling')),
        ('service', _('Service direct selling')),
        ('ptriangles', _('Product triangles deals')),
        ('striangles', _('Service triangles deals')),
        ('entertainment', _('Entertainment expenses')),
        ('social', _('Social expenses provided in kind')),
        ('insurance', _('social expenses for contributions (premiums) for additional social insurance and "Life"')),
        ('voucher', _('The social expenses of food vouchers')),
        ('kind', _('Expenses in kind')),
    ], 'Type deal from taxing view', default='auto',
        help="* The 'Automatic discovery' is used when do not have special tax for other types of the 'Type deal'.\n"
             "* The 'Product direct selling' is used when this tax is configured for standard deal only with "
             "products.\n "
             "* The 'Service direct selling' is used when this tax is configured for standard deal only with "
             "services.\n "
             "* The 'Product triangles deals' is used when this tax is configured for triangles deal only with "
             "products.\n "
             "* The 'Service triangles deals' is used when this tax is configured for triangles deal only with "
             "services.\n "
             "* The 'Entertainment expenses' is used when this tax is configured to calculate base and amount for "
             "'Tax on entertainment expenses'\n "
             "* The 'Social expenses provided in kind' is used when this tax is configured to calculate base and "
             "amount for 'Tax on social expenses provided in kind'\n "
             "* The 'Additional social insurance and Life' is used when this tax is configured to calculate base and "
             "amount for 'Tax on social expenses for contributions (premiums) for additional social insurance and "
             "Life'\n "
             "* The 'The social expenses of food vouchers' is used when this tax is configured to calculate base and "
             "amount for 'Tax on The social expenses of food vouchers'\n "
             "* The 'Expenses in kind' is used when this tax is configured to calculate base and amount for 'Tax on "
             "expenses in kind'\n "
    )

    _sql_constraints = [
        ('invoice_number', 'unique (invoice_number, company_id, type)',
         'The number of the invoice must be unique !'),
        ('protocol_number', 'unique (protocol_number, company_id, type)',
         'The number of the protocol must be unique !'),
        ('ticket_number', 'unique (ticket_number, company_id, type)',
         'The number of the ticket must be unique !'),
        ('customs_number', 'unique (customs_number, company_id, type)',
         'The number of the customs declare be unique !')
    ]

    @api.onchange('fiscal_position_id')
    def _onchange_fiscal_position_id(self):
        if self.fiscal_position_id:
            self.type_docs = self.fiscal_position_id.type_docs

    @api.onchange('type')
    def _onchange_type(self):
        if self.type:
            self.sub_type = self.type in ['in_refund', 'out_refund'] and self.type or 'nosubtype'

    @api.onchange('currency_id')
    def _onchage_currency_id(self):
        if self.currency_id:
            for line in self.invoice_line_ids:
                line.price_unit_vat = 0.0

    @api.multi
    def get_fiscal_position(self):
        delivery_partner_id = self.get_delivery_partner_id()
        return self.env['account.fiscal.position'].get_fiscal_position(self.partner_id, delivery_id=delivery_partner_id)

    @api.onchange('invoice_number', 'ticket_number', 'protocol_number', 'customs_number')
    @api.depends('move_id')
    def onchange_invoice_number(self):
        inv_number = self.number
        if self.move_id and self.type in ('in_invoice', 'in_refund', 'in_debit'):
            self.invoice_number = "%s(%s)" % (inv_number, self.reference)
        if self.move_id and self.invoice_number:
            self.move_id.ref = self.invoice_number
            inv_number = self.invoice_number
        elif self.move_id and self.ticket_number:
            self.move_id.ref = self.ticket_number
            inv_number = self.ticket_number

        if self.move_id and self.protocol_number:
            self.move_id.ref = (
                u"{0} - {1}" if self.move_id.ref else u"{1}"
            ).format(inv_number, self.protocol_number)
        if self.move_id and self.customs_number:
            self.move_id.ref = (
                u"{0} - {1}" if self.move_id.ref else u"{1}"
            ).format(inv_number, self.customs_number)

    @api.model
    def _refund_cleanup_lines_fix(self, lines):
        """ Convert records to dict of values suitable for one2many line creation
            :param recordset lines: records to convert
            :return: list of command tuple for one2many line creation [(0, 0, dict of valueis), ...]
        """
        result = []
        for line in lines:
            values = {}
            for name, field in line._fields.items():
                if name in MAGIC_COLUMNS:
                    continue
                elif field.type == 'many2one':
                    values[name] = line[name].id
                elif field.type not in ['many2many', 'one2many']:
                    values[name] = line[name]
                elif name == 'invoice_line_tax_ids':
                    values[name] = [(6, 0, line[name].ids)]
                elif name == 'analytic_tag_ids':
                    values[name] = [(6, 0, line[name].ids)]
                elif name == 'sale_line_ids':
                    values[name] = [(6, 0, line[name].ids)]
            result.append((0, 0, values))
        return result

    @api.model
    def _refund_cleanup_lines(self, lines):
        # _logger.info("CONTEXT INVOICE REFUND %s" % self._context)
        def get_lines(line, qty=0.0):
            values = {}
            for name, field in line._fields.items():
                if name in MAGIC_COLUMNS:
                    continue
                elif name == 'quantity':
                    values[name] = qty
                elif field.type == 'many2one':
                    values[name] = line[name].id
                elif field.type not in ['many2many', 'one2many']:
                    values[name] = line[name]
                elif name == 'invoice_line_tax_ids':
                    values[name] = [(6, 0, line[name].ids)]
                elif name == 'analytic_tag_ids':
                    values[name] = [(6, 0, line[name].ids)]
                elif name == 'sale_line_ids':
                    values['sale_line_ids'] = [(6, 0, line[name].ids)]
            return values

        if lines._name == 'account.invoice.line' and lines:
            inv = lines[0].invoice_id
            # _logger.info("INVOICE REFUND %s:(%s)" % (inv, self._context))
            if inv and self._context.get('single_product_id'):
                result = []
                product = self._context['single_product_id']
                part = inv.partner_id
                if part.lang:
                    product = product.with_context(lang=part.lang)

                if inv.type in ('out_invoice', 'out_refund'):
                    taxes = product.taxes_id
                else:
                    taxes = product.supplier_taxes_id
                # invoice_line_tax_ids = self.fiscal_position_id.map_tax(taxes, product, inv.partner_id)
                accounts = product.product_tmpl_id.get_product_accounts(inv.fiscal_position_id)
                account = accounts['expense']
                if self.type in ('out_invoice', 'out_refund'):
                    account = accounts['income']
                single_amount = self._context['single_amount']
                if inv.amount_untaxed < single_amount:
                    single_amount = inv.amount_untaxed
                # get all data from credit notes
                single_amount_refunds = {}
                single_amounts = 0.0
                extra_single_amounts = 0.0
                groups = []
                if len(inv.refund_invoice_ids.ids) > 0:
                    for group, group_lines in groupby(lines.sorted(lambda r: r.product_id.id, reverse=True),
                                                      lambda l: l.product_id):
                        groups.append(group)
                    for group, group_lines in groupby(inv.mapped('refund_invoice_ids').mapped('invoice_line_ids').
                                                              sorted(lambda r: r.product_id.id, reverse=True),
                                                      lambda l: l.product_id):
                        single_amount_refunds[group] = sum([x.price_subtotal for x in group_lines])
                        single_amounts += single_amount_refunds[group]
                        if group not in groups:
                            extra_single_amounts = single_amount_refunds[group]
                # _logger.info("AMOUNTS %s:%s" % (single_amounts, single_amount_refunds))
                if self._context.get('separate_account'):
                    amount_untaxed = inv.amount_untaxed - single_amounts
                    for group, group_lines in groupby(lines.sorted(lambda r: r.product_id.id, reverse=True),
                                                      lambda l: l.product_id):
                        if part.lang:
                            group = group.with_context(lang=part.lang)
                        invoice_line_tax_ids = set([])
                        single_amount_refund = 0.0
                        extra_single_amount = 0.0
                        accounts = set([])
                        for inv_line in group_lines:
                            refund_single_amounts = 0.0
                            if single_amount_refunds.get(group):
                                refund_single_amounts = single_amount_refunds[group]
                            if extra_single_amounts > 0:
                                extra_single_amount = extra_single_amounts * (
                                        (inv_line.price_subtotal - refund_single_amounts) / amount_untaxed)
                            single_amount_refund += inv_line.price_subtotal - refund_single_amounts - extra_single_amount
                            invoice_line_tax_ids.update([x.id for x in inv_line.invoice_line_tax_ids])
                            accounts.update([inv_line.account_id])
                        if single_amount_refund <= 0:
                            continue
                        ssingle_amount = single_amount * (single_amount_refund / amount_untaxed)
                        name = group.partner_ref
                        account = accounts and list(accounts)[0] or account
                        if type in ('in_invoice', 'in_refund'):
                            if group.description_purchase:
                                name += '\n' + group.description_purchase
                        else:
                            if group.description_sale:
                                name += '\n' + group.description_sale
                        result.append((0, 0, {'product_id': product.id,
                                              'name': "%s: %s" % (product.name, name),
                                              'quantity': 1.0,
                                              'price_unit': ssingle_amount,
                                              'account_id': account.id,
                                              'invoice_line_tax_ids': [(6, 0, list(invoice_line_tax_ids))]}))
                else:
                    # _logger.info("AMOUNT %s-%s" % (single_amount, single_amounts))
                    single_amount -= single_amounts
                    amount_untaxed = inv.amount_untaxed - single_amounts

                    for tax_line in inv.tax_line_ids:
                        ssingle_amount = single_amount * (tax_line.base / amount_untaxed)
                        invoice_line_tax_ids = [(6, 0, [tax_line.tax_id.id])]
                        result.append((0, 0, {'product_id': product.id,
                                              'quantity': 1.0,
                                              'price_unit': ssingle_amount,
                                              'name': product.name,
                                              'account_id': account.id,
                                              'invoice_line_tax_ids': invoice_line_tax_ids}))
                # _logger.info("RESULT %s" % result)
                return result

        if lines._name == 'account.invoice.line' and lines.mapped('purchase_line_id'):
            # _logger.info("HAS Purchase %s" % lines.mapped('purchase_line_id'))
            result = []
            for line in lines:
                if line.purchase_line_id and line.purchase_line_id.qty_received - line.purchase_line_id.qty_invoiced < 0:
                    result.append((0, 0, get_lines(line, qty=abs(
                        line.purchase_line_id.qty_received - line.purchase_line_id.qty_invoiced))))
                elif not line.purchase_line_id:
                    result.append((0, 0, get_lines(line, qty=line.quantity)))
            return result
        return super(AccountInvoice, self)._refund_cleanup_lines(lines)

    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None):
        # _logger.info("REFUND %s" % self._context)
        result = super(AccountInvoice, self).refund(date_invoice=date_invoice, date=date, description=description,
                                                    journal_id=journal_id)
        if self._context.get('single_product_id'):
            for inv in result:
                inv.tax_line_ids = False
                inv._onchange_invoice_line_ids()
        return result

    @api.multi
    def action_move_create(self):
        for inv in self:
            ticket_number = inv.ticket_number
            customs_number = inv.customs_number
            protocol_number = inv.protocol_number
            custom_number = number = inv.invoice_number

            if not inv.fiscal_position_id:
                inv.fiscal_position_id = inv.env['account.fiscal.position'].with_context(
                    company_id=inv.company_id.id).get_fiscal_position(inv.partner_id.id)

            if not inv.type_docs:
                sequence = inv.journal_id.ticket_sequence_id
                if sequence and inv.type in ('out_invoice', 'out_refund'):
                    sequence = sequence.with_context(
                        ir_sequence_date=inv.date or inv.date_invoice)
                    custom_number = ticket_number = sequence.next_by_id()
                # else:
                #    custom_number = ticket_number = inv.reference
                number = False
            elif inv.type_docs in (False, '', 'standart', 'protocol', 'ictcustoms') and not inv.invoice_number:
                sequence = inv.journal_id.invoice_sequence_id
                if inv.type in ('out_refund', 'in_refund', 'out_debit', 'in_debit'):
                    sequence = inv.journal_id.refund_inv_sequence_id
                if sequence and inv.type in ('out_invoice', 'out_refund', 'out_debit'):
                    sequence = sequence.with_context(
                        ir_sequence_date=inv.date or inv.date_invoice)
                    custom_number = number = sequence.next_by_id()
                # else:
                #    custom_number = number = inv.reference
            elif inv.type_docs in ['ticket'] and inv.type == 'out_invoice' and not inv.ticket_number:
                sequence = inv.journal_id.ticket_sequence_id
                if inv.type in ('out_refund', 'in_refund', 'out_debit', 'in_debit'):
                    sequence = inv.journal_id.refund_inv_sequence_id
                sequence = sequence.with_context(
                    ir_sequence_date=inv.date or inv.date_invoice)
                custom_number = ticket_number = sequence.next_by_id()
                number = False
            elif inv.type_docs == 'protocol' and inv.type in ('in_invoice', 'in_refund') and not inv.protocol_number:
                sequence = inv.journal_id.protocol_sequence_id
                sequence = sequence.with_context(
                    ir_sequence_date=inv.date or inv.date_invoice)
                protocol_number = sequence.next_by_id()
                custom_number = ",".join([custom_number or '', protocol_number])
            elif inv.type_docs == 'customs' and not inv.customs_number and not inv.invoice_number:
                # first get invoice number
                sequence = inv.journal_id.invoice_sequence_id
                if inv.type in ('out_refund', 'in_refund', 'out_debit', 'in_debit'):
                    sequence = inv.journal_id.refund_inv_sequence_id
                if sequence and inv.type in ('out_invoice', 'out_refund', 'out_debit'):
                    sequence = sequence.with_context(
                        ir_sequence_date=inv.date or inv.date_invoice)
                    custom_number = number = sequence.next_by_id()
                else:
                    custom_number = number = inv.reference
                # after the customs number
                sequence = inv.journal_id.customs_sequence_id
                sequence = sequence.with_context(
                    ir_sequence_date=inv.date or inv.date_invoice)
                customs_number = sequence.next_by_id()
                custom_number = ",".join([custom_number or '', customs_number])
            if number or protocol_number or ticket_number or customs_number:
                inv.write({
                    'invoice_number': number,
                    'protocol_number': protocol_number,
                    'ticket_number': ticket_number,
                    'customs_number': customs_number,
                })
        res = super(AccountInvoice, self).action_move_create()
        for inv in self:
            inv.onchange_invoice_number()
        return res

    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        move_lines = super(AccountInvoice, self).finalize_invoice_move_lines(move_lines)
        for inv in self:
            move_lines_base = []
            move_lines_tax = []
            for idx, line in enumerate(move_lines):
                if not self.eu_deals:
                    line[2]['eu_deals'] = not self.eu_deals
                if not self.doc_justification:
                    line[2]['doc_justification'] = not self.doc_justification
                if self.tax_type_deal != 'auto':
                    line[2]['tax_type_deal'] = self.tax_type_deal
                # _logger.info("lines %s:%s" % (idx, line))
                separate_tax = line[2].get('separate') and line[2]['separate'] or False
                if separate_tax:
                    # del line[2]['separate']
                    # _logger.info("SEPARATE %s" % line[2])
                    if separate_tax == 1:
                        line[2]['tax_line_id'] = line[2]['tax_ids'] = False
                    if separate_tax:
                        move_lines_tax.append(line)
                    else:
                        move_lines_base.append(line)
                else:
                    move_lines_base.append(line)
            move_lines = move_lines_base + move_lines_tax

            if inv.type in ('in_refund', 'out_refund'):
                line = []
                for x, y, l in move_lines:
                    l['tax_sign'] = -1
                    line.append((0, 0, l))
                return line
        return move_lines

    def _compare_price_vat(self, line):
        if line.price_unit_vat == 0.0:
            line.price_unit_vat = line.price_unit
        return float_compare(line.price_unit_vat, line.price_unit, precision_rounding=self.currency_id.rounding) != 0

    def _prepare_tax_line_vals(self, line, tax):
        res = super(AccountInvoice, self)._prepare_tax_line_vals(line, tax)
        res.update({
            'amount_currency': tax.get('amount_currency') and tax['amount_currency'] or 0.0,
            'base_currency': tax.get('base_currency') and tax['base_currency'] or 0.0,
        })
        return res

    def _get_taxes_values(self, tax):
        if tax.tax_type_deal and tax.tax_type_deal != 'auto' and tax.tax_type_deal != self.tax_type_deal:
            return True
        return False

    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        taxes_currency = False
        taxes_base = {}
        vals = {}
        round_curr = self.currency_id.round
        round_company_curr = self.company_id.currency_id.round
        for line in self.invoice_line_ids:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            if self._compare_price_vat(line):
                price_unit = line.price_unit_vat * (1 - (line.discount or 0.0) / 100.0)
            ctx = self._context.copy()
            taxes = line.invoice_line_tax_ids.with_context(ctx).compute_all(price_unit, self.currency_id, line.quantity,
                                                                            line.product_id, self.partner_id)['taxes']
            if self.company_id.currency_id != self.currency_id:
                # _logger.info("PRICE %s" % price_unit)
                # Fix incorrect calculations when price is to low move in tax currency like 1 unit price_unit*line.quantity
                price_unit = self.currency_id.with_context(date=self._get_currency_rate_date()).compute(
                    price_unit * line.quantity, self.company_id.currency_id)
                # _logger.info("PRICE %s" % price_unit)
                for tax in taxes:
                    taxes_base[tax['id']] = tax

                if self.type_docs == 'customs' and self.type == 'in_invoice':
                    ctx = dict(ctx, customs_fix=True)
                # Fix calculations with unit price * qty
                taxes_currency = \
                line.invoice_line_tax_ids.with_context(ctx).compute_all(price_unit, self.company_id.currency_id,
                                                                        1.0, line.product_id, self.partner_id)['taxes']
                for tax in taxes_currency:
                    tax.update({
                        'amount_currency': tax['amount'],
                        'base_currency': tax['base'],
                        'amount': ctx.get("customs_fix") and 0.0 or taxes_base[tax['id']]['amount'],
                        'base': taxes_base[tax['id']]['base'],
                    })
                    # _logger.info("TAX CURRENCES %s" % tax)
                    vals[tax['id']] = self._prepare_tax_line_vals(line, tax)
            for tax in taxes:
                tax_data = self.env['account.tax'].browse(tax['id'])
                if self._get_taxes_values(tax_data):
                    continue
                val = self._prepare_tax_line_vals(line, tax)
                key = tax_data.get_grouping_key(val)
                if vals.get(tax['id']):
                    val_currences = vals[tax['id']]
                if key not in tax_grouped:
                    tax_grouped[key] = val
                    tax_grouped[key]['base'] = round_curr(val['base'])
                    if vals.get(tax['id']):
                        tax_grouped[key]['amount_currency'] = val_currences['amount_currency']
                        tax_grouped[key]['base_currency'] = round_company_curr(val_currences['base_currency'])
                else:
                    tax_grouped[key]['amount'] += ctx.get("customs_fix") and 0.0 or val['amount']
                    tax_grouped[key]['base'] += round_curr(val['base'])
                    if vals.get(tax['id']):
                        tax_grouped[key]['amount_currency'] += val_currences['amount_currency']
                        tax_grouped[key]['base_currency'] += round_company_curr(val_currences['base_currency'])

        # _logger.info("TAX GROUPED %s" % tax_grouped)
        return tax_grouped

    @api.model
    def tax_line_move_line_get(self):
        res = []
        # keep track of taxes already processed
        done_taxes = []
        # loop the invoice.tax.line in reversal sequence
        for tax_line in sorted(self.tax_line_ids, key=lambda x: -x.sequence):
            if tax_line.amount_total or tax_line.base:
                tax = tax_line.tax_id
                if tax.amount_type == "group":
                    for child_tax in tax.children_tax_ids:
                        done_taxes.append(child_tax.id)
                res.append({
                    'invoice_tax_line_id': tax_line.id,
                    'tax_line_id': tax_line.tax_id.id,
                    'type': 'tax',
                    'name': tax_line.name,
                    'price_unit': tax_line.amount_total,
                    'quantity': 1,
                    'price': tax_line.amount_total,
                    # 'price_currency': tax_line.amount_currency,
                    'tax_sign': self.type in ['in_refund', 'out_refund'] and -1 or 1,
                    'tax_base': tax_line.base,
                    'tax_base_currency': tax_line.base_currency,
                    'account_id': tax_line.account_id.id,
                    'account_analytic_id': tax_line.account_analytic_id.id,
                    'invoice_id': self.id,
                    'tax_ids': [(6, 0, list(done_taxes))] if tax_line.tax_id.include_base_amount else []
                })
                done_taxes.append(tax.id)
                if tax and \
                        tax.tax_credit_payable in ['taxadvpay', 'eutaxpay', 'eutaxcredit', 'othertax'] and \
                        tax.separate and \
                        tax.contrapart_account_id:
                    if not self.eu_deals and tax.tax_credit_payable == 'eutaxcredit':
                        continue
                    if tax.tax_type_deal and tax.tax_type_deal != self.tax_type_deal:
                        continue
                    res[-1]['separate'] = -1
                    done_taxes.append(tax.id)

                    contrapart_line = res[-1].copy()
                    coef = contrapart_line['price'] > 0.0 and -1 or 1
                    contrapart_line['price'] = abs(contrapart_line['price']) * coef
                    contrapart_line['price_unit'] = abs(contrapart_line['price_unit']) * coef
                    contrapart_line['account_id'] = tax.contrapart_account_id.id
                    contrapart_line['name'] = _("Contrapart for %s" % contrapart_line['name'])
                    contrapart_line['separate'] = 1
                    contrapart_line['type'] = 'taxcontra'
                    res.append(contrapart_line)
                    done_taxes.append(tax.id)
                # elif tax and 'move_period' in tax._fields and \
                #        tax.tax_credit_payable == 'taxcredit' and \
                #        not tax.separate and \
                #        tax.move_period and \
                #        self.date and self.date != self.date_invoice and \
                #        tax.contrapart_period_account_id:
                #
                #    res[-1]['move_period'] = -1
                #    done_taxes.append(tax.id)
                #
                #    contrapart_line = res[-1].copy()
                #    coef = contrapart_line['price'] > 0.0 and -1 or 1
                #    contrapart_line['price'] = abs(contrapart_line['price']) * coef
                #    contrapart_line['price_unit'] = abs(contrapart_line['price_unit']) * coef
                #    contrapart_line['account_id'] = tax.contrapart_period_account_id.id
                #    contrapart_line['name'] = _("Contrapart for %s" % contrapart_line['name'])
                #    contrapart_line['move_period'] = 1
                #    res.append(contrapart_line)
                #    done_taxes.append(tax.id)
                #
                #    contrapart_line = res[-1].copy()
                #    coef = contrapart_line['price'] > 0.0 and -1 or 1
                #    contrapart_line['price'] = abs(contrapart_line['price']) * coef
                #    contrapart_line['price_unit'] = abs(contrapart_line['price_unit']) * coef
                #    contrapart_line['account_id'] = tax.contrapart_period_account_id.id
                #    contrapart_line['name'] = _("Contrapart for %s" % contrapart_line['name'])
                #    del contrapart_line['move_period']
                #    del contrapart_line['tax_line_id']
                #    res.append(contrapart_line)
                #    done_taxes.append(tax.id)
                else:
                    done_taxes.append(tax.id)
        # _logger.info("RES 1 %s" % res)
        return res

    @api.multi
    def compute_invoice_totals(self, company_currency, invoice_move_lines):
        total = 0
        total_currency = 0
        for line in invoice_move_lines:
            tax = False
            if line.get('tax_line_id', False):
                tax = self.env['account.tax'].browse(line['tax_line_id'])

            if self.currency_id != company_currency:
                if tax and tax.tax_credit_payable == 'taxadvpay' and self.type_docs == 'customs' and self.type == 'in_invoice':
                    currency = self.currency_id.with_context(rate_field='rate_statistics',
                                                             date=self._get_currency_rate_date() or fields.Date.context_today(
                                                                 self))
                else:
                    currency = self.currency_id.with_context(
                        date=self._get_currency_rate_date() or fields.Date.context_today(self))
                if not (line.get('currency_id') and line.get('amount_currency')):
                    line['currency_id'] = currency.id
                    line['amount_currency'] = currency.round(line['price'])
                    line['price'] = currency.compute(line['price'], company_currency)
                if line.get('tax_base', False):
                    line['tax_base_currency'] = currency.round(line['tax_base'])
                    line['tax_base'] = currency.compute(line['tax_base'], company_currency)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = self.currency_id.round(line['price'])
                if line.get('tax_base', False):
                    line['tax_base'] = self.currency_id.round(line['tax_base'])

            if tax and tax.tax_credit_payable in ['taxadvpay', 'othertax']:
                continue
            if tax and tax.separate:
                continue

            if self.type in ('out_invoice', 'in_refund'):
                total += line['price']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_currency -= line['amount_currency'] or line['price']

        return total, total_currency, invoice_move_lines

    @api.model
    def line_get_convert(self, line, part):
        res = super(AccountInvoice, self).line_get_convert(line, part)
        if line.get('separate'):
            res['separate'] = line['separate']
        return res

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Credit Note'),
            'in_refund': _('Vendor Credit note'),
            'out_debitnote': _('Customer Debit note'),
            'in_debitnote': _('Vendor Debit Note'),
        }
        result = []
        for inv in self:
            number = False
            number = inv.invoice_number or number
            number = inv.protocol_number or number
            number = inv.ticket_number or number
            number = inv.customs_number or number
            type = inv.sub_type != 'nosubtype' and inv.sub_type or inv.type
            result.append((inv.id, "%s%s%s" % ("%s " % inv.number or TYPES[type], "%s " % inv.name or '',
                                               "(%s)" % number or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('invoice_number', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('protocol_number', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('ticket_number', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('customs_number', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        values = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice=date_invoice, date=date,
                                                             description=description, journal_id=journal_id)
        values['sub_type'] = values['type'] in ['out_refund', 'in_refund'] and values['type'] or 'nosubtype'
        return values

    @api.model
    def _debit_note_cleanup_lines(self, lines):
        """ Convert records to dict of values suitable for one2many line creation
            :param recordset lines: records to convert
            :return: list of command tuple for one2many line creation [(0, 0, dict of valueis), ...]
        """
        result = []
        for line in lines:
            values = {}
            for name, field in line._fields.items():
                if name in MAGIC_COLUMNS:
                    continue
                elif field.type == 'many2one':
                    values[name] = line[name].id
                elif field.type not in ['many2many', 'one2many']:
                    values[name] = line[name]
                elif name == 'invoice_line_tax_ids':
                    values[name] = [(6, 0, line[name].ids)]
                elif name == 'analytic_tag_ids':
                    values[name] = [(6, 0, line[name].ids)]
            result.append((0, 0, values))
        return result

    @api.model
    def _debit_note_tax_lines_account_change(self, lines, taxes_to_change):
        # Let's change the account on tax lines when
        # @param {list} lines: a list of orm commands
        # @param {dict} taxes_to_change
        #   key: tax ID, value: debit note account

        if not taxes_to_change:
            return lines

        for line in lines:
            if isinstance(line[2], dict) and line[2]['tax_id'] in taxes_to_change:
                line[2]['account_id'] = taxes_to_change[line[2]['tax_id']]
        return lines

    def _get_debit_note_common_fields(self):
        return ['partner_id', 'payment_term_id', 'account_id', 'currency_id', 'journal_id']

    @api.model
    def _get_debit_note_prepare_fields(self):
        return ['name', 'reference', 'comment', 'date_due']

    @api.model
    def _get_debit_note_modify_read_fields(self):
        read_fields = ['type', 'number', 'invoice_line_ids', 'tax_line_ids',
                       'date', 'partner_insite', 'partner_contact', 'partner_ref']
        return self._get_debit_note_common_fields() + self._get_debit_note_prepare_fields() + read_fields

    @api.model
    def _get_debit_note_copy_fields(self):
        copy_fields = ['company_id', 'user_id', 'fiscal_position_id']
        return self._get_debit_note_common_fields() + self._get_debit_note_prepare_fields() + copy_fields

    def _get_currency_rate_date(self):
        return self.date or self.date_invoice

    @api.model
    def _prepare_debit_note(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        """ Prepare the dict of values to create the new credit note from the invoice.
            This method may be overridden to implement custom
            credit note generation (making sure to call super() to establish
            a clean extension chain).
            :param record invoice: invoice as credit note
            :param string date_invoice: credit note creation date from the wizard
            :param integer date: force date from the wizard
            :param string description: description of the credit note from the wizard
            :param integer journal_id: account.journal from the wizard
            :return: dict of value to create() the credit note
        """
        values = {}
        for field in self._get_debit_note_copy_fields():
            if invoice._fields[field].type == 'many2one':
                values[field] = invoice[field].id
            else:
                values[field] = invoice[field] or False

        values['invoice_line_ids'] = self._debit_note_cleanup_lines(invoice.invoice_line_ids)

        tax_lines = invoice.tax_line_ids
        taxes_to_change = {
            line.tax_id.id: line.tax_id.account_id.id
            for line in tax_lines.filtered(lambda l: l.tax_id.refund_account_id != l.tax_id.account_id)
        }
        cleaned_tax_lines = self._debit_note_cleanup_lines(tax_lines)
        values['tax_line_ids'] = self._debit_note_tax_lines_account_change(cleaned_tax_lines, taxes_to_change)

        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
        elif invoice['type'] == 'in_invoice':
            journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        else:
            journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        values['journal_id'] = journal.id

        values['sub_type'] = TYPE2DEBITNOTE[invoice.type]
        values['date_invoice'] = date_invoice or fields.Date.context_today(invoice)
        values['date_due'] = values['date_invoice']
        values['state'] = 'draft'
        values['number'] = False
        values['origin'] = invoice.invoice_number or invoice.number
        values['payment_term_id'] = False
        values['debitnote_invoice_id'] = invoice.id

        if values['sub_type'] == 'in_debitnote':
            partner_bank_result = self._get_partner_bank_id(values['company_id'])
            if partner_bank_result:
                values['partner_bank_id'] = partner_bank_result.id

        if date:
            values['date'] = date
        if description:
            values['name'] = description
        return values

    @api.multi
    @api.returns('self')
    def debit_note(self, date_invoice=None, date=None, description=None, journal_id=None):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_debit_note(invoice, date_invoice=date_invoice, date=date,
                                              description=description, journal_id=journal_id)
            # _logger.info("VALUES %s" % values)
            debit_note_invoice = self.create(values)
            invoice_sub_type = {'out_debitnote': ('customer invoices debit note'),
                                'in_debitnote': ('vendor bill debit note')}
            message = _(
                "This %s has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s(%s)</a>") % (
                          invoice_sub_type[debit_note_invoice.sub_type], invoice.id, invoice.number,
                          invoice.invoice_number)
            debit_note_invoice.message_post(body=message)
            new_invoices += debit_note_invoice
        for inv in new_invoices:
            inv.tax_line_ids = False
            inv._onchange_invoice_line_ids()
        return new_invoices

    @api.multi
    def unlink(self):
        """Allow to remove invoices."""
        self.filtered(lambda x: x.journal_id.invoice_sequence_id).write(
            {'move_name': False})
        return super(AccountInvoice, self).unlink()

    @api.multi
    def write(self, vals):
        res = super(AccountInvoice, self).write(vals)
        if 'tax_type_deal' in vals or 'currency_id' in vals:
            for record in self:
                record.compute_taxes()
        return res


accountinvoice.AccountInvoice._refund_cleanup_lines = AccountInvoice._refund_cleanup_lines_fix
accountinvoice.AccountInvoice.tax_line_move_line_get = AccountInvoice.tax_line_move_line_get


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    price_unit_vat = fields.Float(string='VAT Unit Price', digits=dp.get_precision('Product Price'), default=0.0)
    # fix in octa-light state = fields.Selection(related="invoice_id.state")

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        if self.price_unit != 0.0 and self.price_unit_vat != 0.0:
            self.price_unit_vat = self.price_unit


class AccountInvoiceTax(models.Model):
    _inherit = "account.invoice.tax"

    @api.one
    @api.depends('amount_currency')
    def _compute_company_currency_amount(self):
        if self.has_currency:
            self.amount_total_currency = self.amount_currency
        else:
            self.amount_total_currency = 0.0

    @api.one
    @api.depends('invoice_id.company_currency_id', 'invoice_id.currency_id')
    def _compute_has_currency(self):
        self.has_currency = self.invoice_id.company_currency_id != self.invoice_id.currency_id

    @api.depends('invoice_id.invoice_line_ids')
    def _compute_base_amount_currency(self):
        for line in self:
            if line.has_currency:
                tax_grouped = {}
                for invoice in self.mapped('invoice_id'):
                    tax_grouped[invoice.id] = invoice.get_taxes_values()
                for tax in line:
                    tax.base_currency = 0.0
                    if tax.tax_id:
                        key = tax.tax_id.get_grouping_key({
                            'tax_id': tax.tax_id.id,
                            'account_id': tax.account_id.id,
                            'account_analytic_id': tax.account_analytic_id.id,
                        })
                        if tax.invoice_id and key in tax_grouped[tax.invoice_id.id]:
                            tax.base_currency = tax_grouped[tax.invoice_id.id][key]['base_currency']
                            tax.amount_currency = tax_grouped[tax.invoice_id.id][key]['amount_currency']
                        else:
                            _logger.warning(
                                'Tax Base Amount not computable probably due to a change in an underlying tax (%s).',
                                tax.tax_id.name)
            else:
                for tax in line:
                    tax.base_currency = 0.0

    company_currency_id = fields.Many2one('res.currency', related='invoice_id.company_currency_id', readonly=True,
                                          related_sudo=False)
    amount_total_currency = fields.Float(string="Amount total in Company currency",
                                         compute='_compute_company_currency_amount',
                                         currency_field="company_currency_id")
    amount_currency = fields.Float(string="Amount in Company currency", compute='_compute_base_amount_currency',
                                   store=True, currency_field="company_currency_id")
    has_currency = fields.Boolean(compute='_compute_has_currency')
    base_currency = fields.Monetary(string='Base in Company Currency', compute='_compute_base_amount_currency',
                                    store=True, currency_field="company_currency_id")
    tax_credit_payable = fields.Selection(related="tax_id.tax_credit_payable")
