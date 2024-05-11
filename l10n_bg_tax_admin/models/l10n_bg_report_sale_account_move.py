#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMoveBgReportSale(models.Model):
    _name = "account.move.bg.report.sale"
    _inherits = {"account.move": "move_id"}
    _inherit = ["mail.thread", "mail.activity.mixin", "sequence.mixin"]
    _description = "Sale report from POS art. 119(1)"
    _order = "date_creation desc, name desc, id desc"
    _mail_post_access = "read"
    _check_company_auto = True
    _sequence_field = "report_name"
    _sequence_date_field = "report_date"

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
    report_date = fields.Date("Protocol date", copy=False, default=fields.Date.today())
    report_name = fields.Char(
        string="Report Number",
        compute="_compute_report_name",
        inverse="_inverse_report_name",
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
        "report_name",
    )
    def _compute_report_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or "", m.id))

        for report in self:
            move_has_name = report.report_name and report.report_name != "/"
            if move_has_name or report.move_id.state != "posted":
                if not report.posted_before and not report._sequence_matches_date():
                    if report._get_last_sequence(lock=False):
                        # The name does not match the date and the move is not the first in the period:
                        # Reset to draft
                        report.report_name = False
                        continue
                else:
                    if (
                        move_has_name
                        and report.posted_before
                        or not move_has_name
                        and report._get_last_sequence(lock=False)
                    ):
                        continue
            if report.date and (
                not move_has_name or not report._sequence_matches_date()
            ):
                report._set_next_sequence()

        self.filtered(
            lambda m: not m.report_name and not report.quick_edit_mode
        ).report_name = "/"
        self._inverse_report_name()

    def _inverse_report_name(self):
        self.move_id.l10n_bg_name = self.report_name
        self.move_id.l10n_bg_report_sale_date = self.report_date

    def _get_last_sequence_domain(self, relaxed=False):
        # EXTENDS account sequence.mixin
        self.ensure_one()
        if not self.report_date:
            return "WHERE FALSE", {}
        where_string = "WHERE report_name != '/'"
        param = {}

        if not relaxed:
            domain = [
                ("id", "!=", self.id or self._origin.id),
                ("report_name", "not in", ("/", "", False)),
            ]
            reference_move_name = self.search(
                domain + [("report_date", "<=", self.report_date)],
                order="report_date desc",
                limit=1,
            ).report_name
            if not reference_move_name:
                reference_move_name = self.search(
                    domain, order="report_date asc", limit=1
                ).report_name
            sequence_number_reset = self._deduce_sequence_number_reset(
                reference_move_name
            )
            if sequence_number_reset == "year":
                where_string += " AND date_trunc('year', report_date::timestamp without time zone) = date_trunc('year', %(report_date)s) "
                param["report_date"] = self.report_date
                param["anti_regex"] = (
                    re.sub(
                        r"\?P<\w+>",
                        "?:",
                        self._sequence_monthly_regex.split("(?P<seq>")[0],
                    )
                    + "$"
                )
            elif sequence_number_reset == "month":
                where_string += " AND date_trunc('month', report_date::timestamp without time zone) = date_trunc('month', %(report_date)s) "
                param["report_date"] = self.report_date
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

        _logger.info(f"DOMAIN {where_string}::{param}")
        return where_string, param

    def _report_vals(self, move_id):
        return {
            "move_id": move_id.id,
            "report_name": "/",
            "report_date": move_id.invoice_date,
        }
