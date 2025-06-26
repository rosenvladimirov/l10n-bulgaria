#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    get_type_vat,
)

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
    l10n_bg_private_type_vat = fields.Selection(
        related="l10n_bg_private_move_id.l10n_bg_type_vat",
        store=True,
    )
    l10n_bg_private_currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='company_id.currency_id'
    )

    l10n_bg_private_date_creation = fields.Date(
        "Theatrical field with Created Date", required=True, default=fields.Date.today()
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
    currency_id = fields.Many2one(
        string='Protocol Currency (private)',
        related='l10n_bg_private_move_id.company_currency_id', readonly=True,
    )
    l10n_bg_tax_totals = fields.Binary(
        string="Private Totals",
        compute='_compute_l10n_bg_tax_totals',
        exportable=False,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('l10n_bg_private_move_id.posted_before', 'l10n_bg_private_move_id.state', 'l10n_bg_private_move_id.l10n_bg_date')
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
            if (record.l10n_bg_private_move_id.l10n_bg_date and not move_has_l10n_bg_private_name
                and record.l10n_bg_private_move_id.state != 'draft'):
                record._set_next_sequence()
        self._inverse_l10n_bg_private_name()

    def _inverse_l10n_bg_private_name(self):
        self._set_next_made_sequence_gap(False)

    @api.depends('date')
    def _compute_l10n_bg_private_highest_name(self):
        for record in self:
            record.l10n_bg_private_highest_name = record._get_last_sequence()

    @api.depends('l10n_bg_private_move_id.l10n_bg_date', 'move_type', 'l10n_bg_private_name', 'posted_before', 'sequence_number', 'sequence_prefix', 'state')
    def _compute_l10n_bg_private_name_placeholder(self):
        for record in self:
            if (not record.l10n_bg_private_name or record.l10n_bg_private_name == '/') and not record._get_last_sequence():
                sequence_format_string, sequence_format_values = record._get_sequence_format_param(
                    record._get_starting_sequence())
                sequence_format_values['seq'] = sequence_format_values['seq'] + 1
                record.l10n_bg_private_name_placeholder = sequence_format_string.format(**sequence_format_values)
            else:
                record.l10n_bg_private_name_placeholder = False

    @api.depends_context('lang')
    @api.depends('l10n_bg_private_move_id')
    def _compute_l10n_bg_tax_totals(self):
        for private in self:
            move = private.l10n_bg_private_move_id
            if move.is_invoice(include_receipts=True):
                base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
                # Модифицираме tax_details за всеки ред
                for line in base_lines:
                    # Филтрираме само данъците за продажби
                    filtered_taxes_data = [
                        tax_data for tax_data in line['tax_details']['taxes_data']
                        if (tax_data['tax'].mapped('invoice_repartition_line_ids').mapped('tag_ids')
                            or tax_data['tax'].mapped('refund_repartition_line_ids').mapped('tag_ids'))
                           and tax_data['is_reverse_charge']
                    ]
                    for tax_data in filtered_taxes_data:
                        tax_data['tax_amount'] = abs(tax_data['tax_amount'])
                        tax_data['base_amount'] = abs(tax_data['base_amount'])
                        tax_data['tax_amount_currency'] = abs(tax_data['tax_amount_currency'])
                        tax_data['base_amount_currency'] = abs(tax_data['base_amount_currency'])
                    # Обновяваме tax_details само с данъците за продажби
                    line['tax_details']['taxes_data'] = filtered_taxes_data

                l10n_bg_tax_totals = self.env['account.tax']._get_tax_totals_summary(
                    base_lines=base_lines,
                    currency=move.currency_id,
                    company=move.company_id,
                    cash_rounding=move.l10n_bg_private_move_id.invoice_cash_rounding_id,
                )
                l10n_bg_tax_totals['display_in_company_currency'] = (
                    move.company_id.display_invoice_tax_company_currency
                    and move.company_currency_id != move.currency_id
                    and l10n_bg_tax_totals.get('has_tax_groups', False)
                )
                private.l10n_bg_tax_totals = l10n_bg_tax_totals

            else:
                # Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
                private.tax_totals = None

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

    # -------------------------------------------------------------------------
    # Actions buttons
    # -------------------------------------------------------------------------
    def action_post(self):
        res = self.l10n_bg_private_move_id.action_post()
        if not res:
            # Инвалидизираме кеша
            self.invalidate_recordset()
            # Презареждаме записа от базата данни
            self.env.cache.invalidate()
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return res

    def button_cancel(self):
        return self.l10n_bg_private_move_id.button_cancel()

    def button_draft(self):
        return self.l10n_bg_private_move_id.button_draft()

    def action_open_business_doc(self):
        self.ensure_one()
        return {
            'name': _("Vendor Bill"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'account.move',
            'res_id': self.l10n_bg_private_move_id.id,
            'target': 'current',
        }
