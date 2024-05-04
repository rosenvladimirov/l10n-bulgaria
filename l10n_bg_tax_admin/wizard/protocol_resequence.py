#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.date_utils import get_month, get_fiscal_year
from odoo.tools.misc import format_date
from datetime import date
from collections import defaultdict
import json

_logger = logging.getLogger(__name__)

class ReSequenceWizard(models.TransientModel):
    _name = 'protocol.resequence.wizard'
    _description = 'Remake the sequence of Journal Entries.'

    sequence_number_reset = fields.Char(compute='_compute_sequence_number_reset')
    first_date = fields.Date(help="Date (inclusive) from which the numbers are resequenced.")
    end_date = fields.Date(help="Date (inclusive) to which the numbers are resequenced. If not set, all Journal Entries up to the end of the period are resequenced.")
    first_name = fields.Char(compute="_compute_first_name", readonly=False, store=True, required=True, string="First New Sequence")
    ordering = fields.Selection([('keep', 'Keep current order'), ('date', 'Reorder by accounting date')], required=True, default='keep')
    protocol_ids = fields.Many2many('account.move.bg.protocol')
    new_values = fields.Text(compute='_compute_new_values')
    preview_moves = fields.Text(compute='_compute_preview_moves')

    @api.model
    def default_get(self, fields_list):
        """
        Override the default values for the wizard.

        :param fields_list: List of fields for which default values are requested.
        :return: A dictionary of default values.
        """
        values = super(ReSequenceWizard, self).default_get(fields_list)
        if 'protocol_ids' not in fields_list:
            return values
        active_protocol_ids = self.env['account.move.bg.protocol']
        if self.env.context['active_model'] == 'account.move.bg.protocol' and 'active_ids' in self.env.context:
            active_protocol_ids = self.env['account.move.bg.protocol'].browse(self.env.context['active_ids'])
        values['protocol_ids'] = [(6, 0, active_protocol_ids.ids)]
        return values

    @api.depends('first_name')
    def _compute_sequence_number_reset(self):
        """
        Compute the sequence number reset based on the first name.

        Updates the 'sequence_number_reset' field for each record based on the first name of the related protocol.

        :return: None
        """
        for record in self:
            record.sequence_number_reset = record.protocol_ids[0]._deduce_sequence_number_reset(record.first_name)

    @api.depends('protocol_ids')
    def _compute_first_name(self):
        """
        Compute the first name based on associated protocol names.

        Updates the 'first_name' field for each record based on the minimum protocol name among associated protocols.

        :return: None
        """
        self.first_name = ""
        for record in self:
            if record.protocol_ids:
                record.first_name = min(record.protocol_ids._origin.mapped(lambda protocol: protocol.protocol_name or ""))

    @api.depends('new_values', 'ordering')
    def _compute_preview_moves(self):
        """Reduce the computed new_values to a smaller set to display in the preview."""
        for record in self:
            new_values = sorted(json.loads(record.new_values).values(), key=lambda x: x['server-date'], reverse=True)
            changeLines = []
            in_elipsis = 0
            previous_line = None
            for i, line in enumerate(new_values):
                if i < 3 or i == len(new_values) - 1 or line['new_by_name'] != line['new_by_date'] \
                 or (self.sequence_number_reset == 'year' and line['server-date'][0:4] != previous_line['server-date'][0:4])\
                 or (self.sequence_number_reset == 'year_range' and line['server-year-start-date'][0:4] != previous_line['server-year-start-date'][0:4])\
                 or (self.sequence_number_reset == 'month' and line['server-date'][0:7] != previous_line['server-date'][0:7]):
                    if in_elipsis:
                        changeLines.append({'id': 'other_' + str(line['id']), 'current_name': _('... (%s other)', in_elipsis), 'new_by_name': '...', 'new_by_date': '...', 'date': '...'})
                        in_elipsis = 0
                    changeLines.append(line)
                else:
                    in_elipsis += 1
                previous_line = line

            record.preview_moves = json.dumps({
                'ordering': record.ordering,
                'changeLines': changeLines,
            })

    @api.depends('first_name', 'protocol_ids', 'sequence_number_reset')
    def _compute_new_values(self):
        """Compute the proposed new values.

        Sets a JSON string on new_values representing a dictionary that maps account.move.bg.protocol
        ids to a dictionary containing the name if we execute the action, and information
        relative to the preview widget.
        """
        def _get_move_key(protocol_id):
            company = protocol_id.company_id
            year_start, year_end = get_fiscal_year(protocol_id.date, day=company.fiscalyear_last_day, month=int(company.fiscalyear_last_month))
            if self.sequence_number_reset == 'year':
                return protocol_id.date.year
            elif self.sequence_number_reset == 'year_range':
                return "%s-%s"%(year_start.year, year_end.year)
            elif self.sequence_number_reset == 'month':
                return (protocol_id.date.year, protocol_id.date.month)
            return 'default'

        self.new_values = "{}"
        for record in self.filtered('first_name'):
            protocols_by_period = defaultdict(lambda: record.env['account.move.bg.protocol'])
            for protocol in record.protocol_ids._origin:  # Sort the moves by period depending on the sequence number reset
                protocols_by_period[_get_move_key(protocol)] += protocol

            seq_format, format_values = record.protocol_ids[0]._get_sequence_format_param(record.first_name)
            format_values['year_end_length'] = len(str(date.today().year))  # Set year_end_length based on the current year
            sequence_number_reset = record.protocol_ids[0]._deduce_sequence_number_reset(record.first_name)

            new_values = {}
            for j, period_recs in enumerate(protocols_by_period.values()):
                # compute the new values period by period
                year_start, year_end = period_recs[0]._get_sequence_date_range(sequence_number_reset)
                _logger.info(f'RESET {year_start}')
                for protocol in period_recs:
                    new_values[protocol.id] = {
                        'id': protocol.id,
                        'current_name': protocol.protocol_name,
                        'state': protocol.state,
                        'date': format_date(self.env, protocol.date),
                        'server-date': str(protocol.date),
                        'server-year-start-date': str(year_start),
                    }

                new_name_list = [seq_format.format(**{
                    **format_values,
                    'month': year_start.month,
                    'year_end': year_end.year % (10 ** format_values['year_end_length']),
                    'year': year_start.year % (10 ** format_values['year_length']),
                    'seq': i + (format_values['seq'] if j == (len(protocols_by_period)-1) else 1),
                }) for i in range(len(period_recs))]

                # For all the protocols of this period, assign the name by increasing initial name
                for protocol, new_name in zip(period_recs.sorted(lambda m: (m.sequence_prefix, m.sequence_number)), new_name_list):
                    new_values[protocol.id]['new_by_name'] = new_name
                # For all the protocols of this period, assign the name by increasing date
                for protocol, new_name in zip(period_recs.sorted(lambda m: (m.date, m.protocol_name or "", m.id)), new_name_list):
                    new_values[protocol.id]['new_by_date'] = new_name

            record.new_values = json.dumps(new_values)

    def resequence(self):
        """
        Resequence the protocols based on the provided new values.

        :raises UserError: If reordering by date is attempted when the journal is locked with a hash.
        """
        new_values = json.loads(self.new_values)
        if self.protocol_ids.journal_id and self.protocol_ids.journal_id.restrict_mode_hash_table:
            if self.ordering == 'date':
                raise UserError(_('You can not reorder sequence by date when the journal is locked with a hash.'))
        protocols_to_rename = self.env['account.move.bg.protocol'].browse(int(k) for k in new_values.keys())
        protocols_to_rename.protocol_name = '/'
        protocols_to_rename.flush_recordset(["protocol_name"])
        # If the db is not forcibly updated, the temporary renaming could only happen in cache and still trigger the constraint

        for protocol_id in self.protocol_ids:
            if str(protocol_id.id) in new_values:
                if self.ordering == 'keep':
                    protocol_id.protocol_name = new_values[str(protocol_id.id)]['new_by_name']
                else:
                    protocol_id.protocol_name = new_values[str(protocol_id.id)]['new_by_date']
