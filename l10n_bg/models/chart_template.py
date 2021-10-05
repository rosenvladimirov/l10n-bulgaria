# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    tax_credit_payable = fields.Selection([('taxcredit', 'Tax credit receivable from the taxpayer'),
                                           ('taxpay', 'Tax payable by the taxpayer'),
                                           ('eutaxcredit', 'Tax credit receivable from the taxpayer on EU deals'),
                                           ('eutaxpay', 'Tax payable by the taxpayer on EU deals'),
                                           ('taxadvpay', 'Tax payable by the taxpayer when Imports from outside EU'),
                                           ('taxbalance', 'Account for balance of taxes'),
                                           ('othertax', 'Different by VAT Tax payable by the taxpayer')],
                                          'Who pays tax', required=True, default='taxpay',
                                          help="If not applicable (computed through a Python code), the tax won't "
                                               "appear on the invoice.Who pays the tax purchaser or seller ( for "
                                               "imports from outside the EU pay the buyer )")

    separate = fields.Boolean('Separate movement')
    contrapart_account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)],
                                            string='Contrapart Account', ondelete='restrict',
                                            help="Account that will be set when work with separated movement for "
                                                 "contra part. Leave empty to use the contrapart account.")

    def _get_tax_vals(self, company, tax_template_to_tax):
        val = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        val.update(dict(tax_credit_payable=self.tax_credit_payable,
                        separate=self.separate,
                        contrapart_account_id=self.contrapart_account_id))
        return val


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.multi
    def create_record_with_xmlid(self, company, template, model, vals):
        if model == 'account.fiscal.position':
            vals['type_docs'] = template.type_docs
        return super(AccountChartTemplate, self).create_record_with_xmlid(company, template, model, vals)

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company_id, journals_dict=None):
        self.ensure_one()
        journal_data = super(AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company_id, journals_dict=journals_dict,
        )
        if not self.is_bulgarian_chart():  # pragma: no cover
            return journal_data
        journal_model = self.env['account.journal']
        # Create unified sequence for journal entries
        generic_journal_seq = self.env.ref(
            'l10n_bg.sequence_bulgarian_journal',
        )

        for journal_vals in journal_data:
            if journal_vals['type'] in ('sale'):
                seq = generic_journal_seq.copy({
                    'name': _('Journal Invoice Sequence'),
                    'active': True,
                    'company_id': company_id.id,
                })
                journal_vals['invoice_sequence_id'] = seq.id
                seq = generic_journal_seq.copy({
                    'name': _('Journal (Refund) Invoice Sequence'),
                    'prefix': '1',
                    'active': True,
                    'company_id': company_id.id,
                })
                journal_vals['refund_inv_sequence_id'] = seq.id
                seq = generic_journal_seq.copy({
                    'name': _('Journal Ticket Sequence'),
                    'active': True,
                    'company_id': company_id.id,
                })
                journal_vals['ticket_sequence_id'] = seq.id
            elif journal_vals['type'] in ('purchase'):
                seq = generic_journal_seq.copy({
                    'name': _('Journal Protocol Sequence'),
                    'prefix': '2',
                    'active': True,
                    'company_id': company_id.id,
                })
                journal_vals['protocol_sequence_id'] = seq.id
                seq = generic_journal_seq.copy({
                    'name': _('Journal Customs Sequence'),
                    'prefix': '%range_year)s/',
                    'padding': 0,
                    'active': True,
                    'company_id': company_id.id,
                })
                journal_vals['customs_sequence_id'] = seq.id
        return journal_data

    @api.model
    def _get_bulgarian_charts_xml_ids(self):
        return [
            'l10n_bg.bg_chart_template',
        ]

    @api.multi
    def _get_bulgarian_charts(self):
        charts = self.env['account.chart.template']
        for chart_id in self._get_bulgarian_charts_xml_ids():
            charts |= self.env.ref(chart_id)
        return charts

    @api.multi
    @tools.ormcache('self')
    def is_bulgarian_chart(self):
        return self in self._get_bulgarian_charts()


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    type_docs = fields.Selection([('standart', 'Standart for invoices'),
                                  ('ticket', 'B2C Invoices'),
                                  ('customs', 'Customs declaration'),
                                  ('protocol', 'Swap incoming invoices with a protocol')], string="Types of docs",
                                 default='standart')
