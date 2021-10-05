# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, exceptions


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    invoice_sequence_id = fields.Many2one(
        comodel_name='ir.sequence', string='Invoice sequence',
        domain="[('company_id', '=', company_id)]", ondelete='restrict',
        help="The sequence used for invoice numbers in this journal.",
    )
    refund_inv_sequence_id = fields.Many2one(
        comodel_name='ir.sequence', string='Refund sequence',
        domain="[('company_id', '=', company_id)]", ondelete='restrict',
        help="The sequence used for refund invoices numbers in this journal.",
    )
    protocol_sequence_id = fields.Many2one(
        comodel_name='ir.sequence', string='Protocol sequence',
        domain="[('company_id', '=', company_id)]", ondelete='restrict',
        help="The sequence used for protocol numbers in this journal.",
    )
    ticket_sequence_id = fields.Many2one(
        comodel_name='ir.sequence', string='Ticket sequence',
        domain="[('company_id', '=', company_id)]", ondelete='restrict',
        help="The sequence used for Ticket (invoice) numbers in this journal.",
    )
    customs_sequence_id = fields.Many2one(
        comodel_name='ir.sequence', string='Customs sequence',
        domain="[('company_id', '=', company_id)]", ondelete='restrict',
        help="The sequence used for Customs declar numbers in this journal.",
    )

    @api.multi
    @api.constrains('invoice_sequence_id')
    def _check_company(self):
        for journal in self:
            sequence_company = journal.invoice_sequence_id.company_id
            if sequence_company and sequence_company != journal.company_id:
                raise exceptions.Warning(
                    _("Journal company and invoice sequence company do not "
                      "match."))

    @api.multi
    @api.constrains('protocol_sequence_id')
    def _check_company(self):
        for journal in self:
            sequence_company = journal.protocol_sequence_id.company_id
            if sequence_company and sequence_company != journal.company_id:
                raise exceptions.Warning(
                    _("Journal company and protocol sequence company do not "
                      "match."))

    @api.multi
    @api.constrains('refund_inv_sequence_id')
    def _check_company_refund(self):
        for journal in self:
            sequence_company = journal.refund_inv_sequence_id.company_id
            if sequence_company and sequence_company != journal.company_id:
                raise exceptions.Warning(
                    _("Journal company and refund sequence company do not "
                      "match."))

    @api.model
    def create(self, vals):
        if not vals.get('company_id') or vals.get('sequence_id'):
            return super(AccountJournal, self).create(vals)
        company = self.env['res.company'].browse(vals['company_id'])
        if company.chart_template_id.is_bulgarian_chart():
            generic_journal_seq = self.env.ref('l10n_bg.sequence_bulgarian_journal', )
            if vals['type'] in ('sale'):
                seq = generic_journal_seq.copy({
                    'name': _('Journal Invoice Sequence'),
                    'active': True,
                    'company_id': company.id,
                })
                vals['invoice_sequence_id'] = seq.id
                seq = generic_journal_seq.copy({
                    'name': _('Journal (Refund) Invoice Sequence'),
                    'prefix': '1',
                    'active': True,
                    'company_id': company.id,
                })
                vals['refund_inv_sequence_id'] = seq.id
                seq = generic_journal_seq.copy({
                    'name': _('Journal Ticket Sequence'),
                    'active': True,
                    'company_id': company.id,
                })
                vals['ticket_sequence_id'] = seq.id
            elif vals['type'] in ('purchase'):
                seq = generic_journal_seq.copy({
                    'name': _('Journal Protocol Sequence'),
                    'prefix': '2',
                    'active': True,
                    'company_id': company.id,
                })
                vals['protocol_sequence_id'] = seq.id
                seq = generic_journal_seq.copy({
                    'name': _('Journal Customs Sequence'),
                    'prefix': '%(range_year)s/',
                    'padding': 0,
                    'active': True,
                    'company_id': company.id,
                })
                vals['customs_sequence_id'] = seq.id
        return super(AccountJournal, self).create(vals)
