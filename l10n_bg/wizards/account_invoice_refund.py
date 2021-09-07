# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    filter_refund = fields.Selection(selection_add=[
                                    ('amount', 'Create a draft debit/credit note for amount corrections'),
                                    ('debitnote', 'Create a draft debit note'),
                                    # ('so_po', 'Create a draft credit note from SO/PO'),
                                    ],
                                     string='Correction Method')
    default_scouting_product_id = fields.Many2one('product.product', 'Scouting Product', domain="[('type', '=', 'service')]",
        help='Default product used for credit or debit scouting')
    amount = fields.Float('Amount for corrections')
    account_separate = fields.Boolean('Separate by Account')

    @api.onchange('default_scouting_product_id')
    @api.depends('description')
    def _onchange_default_scouting_product_id(self):
        if not self.description and self.filter_refund == 'amount':
            self.description = _('Amount corrections with %s') % self.default_scouting_product_id.display_name

    @api.onchange('filter_refund')
    @api.depends('default_scouting_product_id')
    def _onchage_filter_refund(self):
        if self.filter_refund != 'amount':
            self.default_scouting_product_id = False

    @api.multi
    def compute_debit_note(self, mode='debitnote'):
        inv_obj = self.env['account.invoice']
        inv_tax_obj = self.env['account.invoice.tax']
        inv_line_obj = self.env['account.invoice.line']
        context = dict(self._context or {})
        xml_id = False

        for form in self:
            created_inv = []
            date = False
            description = False
            for inv in inv_obj.browse(context.get('active_ids')):
                if inv.state in ['draft', 'cancel']:
                    raise UserError(_('Cannot create debit note for the draft/cancelled invoice.'))
                if inv.reconciled and mode in ('cancel', 'modify'):
                    raise UserError(_(
                        'Cannot create a debit note for the invoice which is already reconciled, invoice should be unreconciled first, then only you can add credit note for this invoice.'))

                date = form.date or False
                description = form.description or inv.name
                debit_note = inv.debit_note(form.date_invoice, date, description, inv.journal_id.id)

                created_inv.append(debit_note.id)
                if mode in ('cancel', 'modify'):
                    movelines = inv.move_id.line_ids
                    to_reconcile_ids = {}
                    to_reconcile_lines = self.env['account.move.line']
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            to_reconcile_lines += line
                            to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                        if line.reconciled:
                            line.remove_move_reconcile()
                    debit_note.action_invoice_open()
                    for tmpline in debit_note.move_id.line_ids:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_lines += tmpline
                    to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                    if mode == 'modify':
                        invoice = inv.read(inv_obj._get_debit_note_modify_read_fields())
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
                        invoice_lines = inv_obj.with_context(mode='modify')._debit_note_cleanup_lines(invoice_lines)
                        tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
                        tax_lines = inv_obj._debit_note_cleanup_lines(tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'sub_type': inv.sub_type,
                            'date_invoice': form.date_invoice,
                            'state': 'draft',
                            'number': False,
                            'invoice_line_ids': invoice_lines,
                            'tax_line_ids': tax_lines,
                            'date': date,
                            'origin': inv.origin,
                            'fiscal_position_id': inv.fiscal_position_id.id,
                        })
                        for field in inv_obj._get_debit_note_common_fields():
                            if inv_obj._fields[field].type == 'many2one':
                                invoice[field] = invoice[field] and invoice[field][0]
                            else:
                                invoice[field] = invoice[field] or False
                        inv_debit_note = inv_obj.create(invoice)
                        if inv_debit_note.payment_term_id.id:
                            inv_debit_note._onchange_payment_term_date_invoice()
                        created_inv.append(inv_debit_note.id)
                xml_id = inv.type == 'out_invoice' and 'action_invoice_out_debit_note' or \
                         inv.type == 'out_refund' and 'action_invoice_tree1' or \
                         inv.type == 'in_invoice' and 'action_invoice_in_debit_note' or \
                         inv.type == 'in_refund' and 'action_invoice_tree2'
                # Put the reason in the chatter
                subject = _("Debit Note")
                body = description
                debit_note.message_post(body=body, subject=subject)
        if xml_id:
            if xml_id in ['action_invoice_tree1', 'action_invoice_tree2']:
                result = self.env.ref('account.%s' % (xml_id)).read()[0]
            else:
                result = self.env.ref('l10n_bg.%s' % (xml_id)).read()[0]
            invoice_domain = safe_eval(result['domain'])
            invoice_domain.append(('id', 'in', created_inv))
            result['domain'] = invoice_domain
            return result
        return True

    # @api.multi
    # def compute_so_po(self, mode='so_po'):
    #     inv_obj = self.env['account.invoice']
    #     context = dict(self._context or {})
    #
    #     for form in self:
    #         created_inv = []
    #         date = False
    #         description = False
    #         for inv in inv_obj.browse(context.get('active_ids')):
    #             date = form.date or False
    #             description = form.description or inv.name
    #             credit_note = inv.debit_note(form.date_invoice, date, description, inv.journal_id.id)
    #     return True

    @api.multi
    def invoice_refund(self):
        data_refund_debitnote = self.read(['filter_refund'])[0]['filter_refund']
        if data_refund_debitnote == 'debitnote':
            return self.with_context(dict(self._context, single_product_id=self.default_scouting_product_id, single_amount=self.amount, separate_account=self.account_separate)).compute_debit_note(data_refund_debitnote)
        return self.with_context(dict(self._context, single_product_id=self.default_scouting_product_id, single_amount=self.amount, separate_account=self.account_separate)).compute_refund(data_refund_debitnote)
