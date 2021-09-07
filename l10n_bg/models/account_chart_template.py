from openerp import _, api, models, tools


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company_id,
                              journals_dict=None):
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
