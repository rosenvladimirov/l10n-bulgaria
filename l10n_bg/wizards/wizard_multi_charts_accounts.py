# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.multi
    def _create_bank_journals_from_o2m(self, company, acc_template_ref):
        journal_model = self.env['account.journal']
        journals = journal_model.search([('company_id', '=', company.id)])
        res = super(WizardMultiChartsAccounts, self)._create_bank_journals_from_o2m(company, acc_template_ref)

        if not self.chart_template_id.is_bulgarian_chart():
            return res
        journals2 = journal_model.search([('company_id', '=', company.id)])
        new_journals = journals2 - journals
        sequence = self.env['ir.sequence'].search([
            ('name', '=', _('Journal Entries Sequence')),
            ('company_id', '=', company.id)
        ], limit=1,
        )
        new_journals.write({
            'sequence_id': sequence.id,
        })
        return res
