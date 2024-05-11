#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re

from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMoveBgProtocol(models.Model):
    _name = "account.move.bg.protocol"
    _inherits = {"account.move": "move_id"}
    _inherit = ["mail.thread", "mail.activity.mixin", "sequence.mixin"]
    _description = "VAT Protocol for invoice art. 117(2)"
    _order = "date_creation desc, name desc, id desc"
    _mail_post_access = "read"
    _check_company_auto = True
    _sequence_field = "protocol_name"
    _sequence_date_field = "protocol_date"

    move_id = fields.Many2one(
        "account.move",
        string="Account invoice",
        ondelete="cascade",
        required=True,
        index=True,
    )
    date_creation = fields.Date(
        "Created Date", required=True, default=fields.Date.today()
    )
    protocol_date = fields.Date(
        "Protocol date", copy=False, default=fields.Date.today()
    )
    protocol_name = fields.Char(
        string="Protocol Number",
        compute="_compute_protocol_name",
        inverse="_inverse_protocol_name",
        readonly=False,
        store=True,
        copy=False,
        tracking=True,
        index="trigram",
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends(
        "move_id.posted_before",
        "move_id.state",
        "move_id.journal_id",
        "move_id.date",
        "protocol_date",
    )
    def _compute_protocol_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or "", m.id))

        for protocol in self:
            move_has_name = protocol.protocol_name and protocol.protocol_name != "/"
            if move_has_name or protocol.move_id.state != "posted":
                if not protocol.posted_before and not protocol._sequence_matches_date():
                    if protocol._get_last_sequence(lock=False):
                        # The name does not match the date and the move is not the first in the period:
                        # Reset to draft
                        protocol.protocol_name = False
                        continue
                else:
                    if (
                        move_has_name
                        and protocol.posted_before
                        or not move_has_name
                        and protocol._get_last_sequence(lock=False)
                    ):
                        continue
            if protocol.date and (
                not move_has_name or not protocol._sequence_matches_date()
            ):
                protocol._set_next_sequence()

        self.filtered(
            lambda m: not m.protocol_name and not protocol.quick_edit_mode
        ).protocol_name = "/"
        self._inverse_protocol_name()

    def _inverse_protocol_name(self):
        self.move_id.l10n_bg_name = self.protocol_name
        self.move_id.l10n_bg_protocol_date = self.protocol_date

    def _get_last_sequence_domain(self, relaxed=False):
        # EXTENDS account sequence.mixin
        self.ensure_one()
        if not self.protocol_date:
            return "WHERE FALSE", {}
        where_string = "WHERE protocol_name != '/'"
        param = {}

        if not relaxed:
            domain = [
                ("id", "!=", self.id or self._origin.id),
                ("protocol_name", "not in", ("/", "", False)),
            ]
            reference_move_name = self.search(
                domain + [("protocol_date", "<=", self.protocol_date)],
                order="protocol_date desc",
                limit=1,
            ).protocol_name
            if not reference_move_name:
                reference_move_name = self.search(
                    domain, order="protocol_date asc", limit=1
                ).protocol_name
            sequence_number_reset = self._deduce_sequence_number_reset(
                reference_move_name
            )
            if sequence_number_reset == "year":
                where_string += " AND date_trunc('year', protocol_date::timestamp without time zone) = date_trunc('year', %(protocol_date)s) "
                param["protocol_date"] = self.protocol_date
                param["anti_regex"] = (
                    re.sub(
                        r"\?P<\w+>",
                        "?:",
                        self._sequence_monthly_regex.split("(?P<seq>")[0],
                    )
                    + "$"
                )
            elif sequence_number_reset == "month":
                where_string += " AND date_trunc('month', protocol_date::timestamp without time zone) = date_trunc('month', %(protocol_date)s) "
                param["protocol_date"] = self.protocol_date
            else:
                param["anti_regex"] = (
                    re.sub(
                        r"\?P<\w+>",
                        "?:",
                        self._sequence_yearly_regex.split("(?P<seq>")[0],
                    )
                    + "$"
                )

            if param.get("anti_regex"):
                where_string += " AND sequence_prefix !~ %(anti_regex)s "

        # _logger.info(f"DOMAIN {where_string}::{param}")
        return where_string, param

    def _protocol_vals(self, move_id):
        return {
            "move_id": move_id.id,
            "protocol_name": "/",
            "protocol_date": move_id.invoice_date,
        }

    def _get_name_protocol_report(self):
        self.ensure_one()
        return "account.report_protocol_document"

    def _protocols_aml(self, invoice_id, new_entry_id, map_id):
        # Create new account moves
        base_lines = invoice_id.invoice_line_ids.filtered(
            lambda r: r.display_type == "product"
        )
        amount_currency_total = 0.0
        factor_percent = map_id.factor_percent == 0.0 and 100.0 or map_id.factor_percent
        for line in base_lines:
            amount_currency_total += line.amount_currency
        amount_currency_total *= factor_percent / 100
        account_id = (
            map_id.account_id
            and map_id.account_id
            or invoice_id.company_id.account_journal_suspense_account_id
        )
        tax_ids = account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == "sale")
        if not tax_ids:
            tax_ids = invoice_id.company_id.account_purchase_tax_id
        if tax_ids and new_entry_id.fiscal_position_id:
            tax_ids = new_entry_id.fiscal_position_id.map_tax(tax_ids)
        aml_vals_list = [
            Command.create(
                {
                    "display_type": "product",
                    "account_id": account_id.id,
                    "partner_id": new_entry_id.partner_id.id,
                    "currency_id": invoice_id.currency_id.id,
                    "amount_currency": amount_currency_total,
                    "balance": amount_currency_total * invoice_id.l10n_bg_currency_rate,
                    "l10n_bg_private_vat_invoice_id": invoice_id.id,
                    "tax_ids": [Command.set(tax_ids.ids)],
                }
            )
        ]
        return aml_vals_list
