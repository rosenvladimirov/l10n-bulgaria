#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMoveBgPrivate(models.Model):
    _name = "account.move.bg.private"
    _inherits = {"account.move": "l10n_bg_private_move_id"}
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin', 'sequence.mixin']
    _description = "VAT Protocol for private usage invoices art. 117(2)"
    _order = "l10n_bg_private_date_creation desc, l10n_bg_private_name desc, id desc"
    _mail_post_access = "read"
    _check_company_auto = True
    _sequence_field = "l10n_bg_private_name"

    l10n_bg_private_move_id = fields.Many2one(
        "account.move",
        string="Account invoice",
        ondelete="cascade",
        required=True,
        index=True,
    )
    l10n_bg_private_invoice_ids = fields.Many2many(
        "account.move",
        "invoices_private_vat_rel",
        "private_id",
        "invoice_id",
        string="Used invoices for private vat",
        check_company=True,
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )


    l10n_bg_private_date_creation = fields.Date(
        "Theatrical field with Created Date", required=True, default=fields.Date.today()
    )

    l10n_bg_private_private_type = fields.Selection(
        [
            ('117', 'Art. 117 (2)'),
            ('117_debit', 'Debit Art. 117 (2)'),
            ('117_credit', 'Credit Art. 117 (2)'),
        ],
        string="Private document Type",
        default='117',
        required=True,
    )
    l10n_bg_private_name = fields.Char(
        string="Private Document Number",
        compute="_compute_l10n_bg_private_name",
        inverse="_inverse_l10n_bg_private_name",
        readonly=False,
        store=True,
        copy=False,
        tracking=True,
        index="trigram",
    )
    l10n_bg_private_name_placeholder = fields.Char(compute='_compute_l10n_bg_private_name_placeholder')
    l10n_bg_private_highest_name = fields.Char(compute='_compute_l10n_bg_private_highest_name')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('l10n_bg_private_move_id.posted_before', 'l10n_bg_private_move_id.state', 'l10n_bg_private_move_id.l10n_bg_private_date')
    def _compute_l10n_bg_private_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or '', m._origin.id))

        for record in self:
            if record.l10n_bg_private_move_id.state == 'cancel':
                continue

            move_has_l10n_bg_private_name = record.l10n_bg_private_name and record.l10n_bg_private_name != '/'
            if not record.l10n_bg_private_move_id.posted_before:
                # The name does not match the date, and the move is not the first in the period:
                # Reset to draft
                record.l10n_bg_private_name = False
                continue
            if (record.l10n_bg_private_move_id.l10n_bg_private_date and not move_has_l10n_bg_private_name
                and record.l10n_bg_private_move_id.state != 'draft'):
                record._set_next_sequence()
        self._inverse_l10n_bg_private_name()

    def _inverse_l10n_bg_private_name(self):
        self._set_next_made_sequence_gap(False)

    @api.depends('date')
    def _compute_l10n_bg_private_highest_name(self):
        for record in self:
            record.l10n_bg_private_highest_name = record._get_last_sequence()

    @api.depends('l10n_bg_private_move_id.l10n_bg_private_date', 'move_type', 'l10n_bg_private_name', 'posted_before', 'sequence_number', 'sequence_prefix', 'state')
    def _compute_l10n_bg_private_name_placeholder(self):
        for record in self:
            if (not record.l10n_bg_private_name or record.l10n_bg_private_name == '/') and not record._get_last_sequence():
                sequence_format_string, sequence_format_values = record._get_sequence_format_param(
                    record._get_starting_sequence())
                sequence_format_values['seq'] = sequence_format_values['seq'] + 1
                record.l10n_bg_private_name_placeholder = sequence_format_string.format(**sequence_format_values)
            else:
                record.l10n_bg_private_name_placeholder = False

    # -------------------------------------------------------------------------
    # SEQUENCE MIXIN
    # -------------------------------------------------------------------------
    def _get_last_sequence_domain(self, relaxed=False):
        self.ensure_one()
        where_string = "WHERE l10n_bg_private_name != '/'"
        param = {}
        if not relaxed:
            param['anti_regex'] = self._make_regex_non_capturing(self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'
        return where_string, param

    def _get_starting_sequence(self):
        self.ensure_one()
        return "0"*10

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        res = super()._get_last_sequence(relaxed=relaxed, with_prefix=with_prefix)
        padded_number = res.replace(with_prefix, '') if with_prefix else res
        padded_number = padded_number and padded_number.zfill(10) or ''
        res = with_prefix + padded_number[len(with_prefix):] if with_prefix else padded_number
        return res

    def _set_next_made_sequence_gap(self, made_gap: bool):
        """Update the field made_sequence_gap on the next moves of the current ones.

        Either:
        - we changed something related to the sequence on the current moves, so we need to set the
          sequence as broken on the next moves before updating (made_gap=True)
        - we are filling a gap, so we need to update the next move to remove the flag (made_gap=False)
        """
        next_privates = self.browse()
        named = self.filtered(lambda m: m.l10n_bg_private_name and m.l10n_bg_private_name != '/')
        for prefix, privates in named.grouped(lambda move: move.sequence_prefix).items():
            next_privates += self.env['account.move'].sudo().search([
                ('sequence_prefix', '=', prefix),
                ('sequence_number', 'in', [move.sequence_number + 1 for move in next_privates]),
            ])
        next_privates.made_sequence_gap = made_gap

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            if name_node := arch.xpath("""//field[@name="l10n_bg_private_name"][@invisible="l10n_bg_private_name == '/' and not posted_before and not quick_edit_mode"]"""):
                name_node[0].set('invisible', "not (name or l10n_bg_private_name_placeholder or quick_edit_mode)")
            if draft_node := arch.xpath("""//span[@invisible="l10n_bg_private_name == '/' and not posted_before and not quick_edit_mode"]"""):
                draft_node[0].set('invisible', "l10n_bg_private_name or l10n_bg_private_name_placeholder or quick_edit_mode")
        return arch, view
