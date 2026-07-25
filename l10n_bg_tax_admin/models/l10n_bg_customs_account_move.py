#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMoveBgCustoms(models.Model):
    _name = "account.move.bg.customs"
    _inherits = {"account.move": "move_id"}
    _inherit = ["mail.thread", "mail.activity.mixin", "sequence.mixin"]
    _description = "Customs declarations"
    _order = "date_creation desc, name desc, id desc"
    _mail_post_access = "read"
    _check_company_auto = True
    _sequence_field = "customs_name"
    _sequence_date_field = "customs_date"

    move_id = fields.Many2one(
        "account.move",
        string="Account invoice",
        ondelete="cascade",
        required=True,
        index=True,
    )
    date_creation = fields.Date(
        "Created Date", required=True, default=fields.Date.today
    )
    customs_date = fields.Date("Date", copy=False, default=fields.Date.today)
    customs_name = fields.Char(
        string="Customs Number",
        copy=False,
        tracking=True,
        index="trigram",
    )
    mrn = fields.Char(
        string="MRN",
        size=20,
        copy=False,
        tracking=True,
        index="trigram",
        help="Movement Reference Number from the customs declaration "
        "(20 characters). Entered manually from the real document.",
    )

    _sql_constraints = [
        (
            "mrn_unique",
            "unique(mrn)",
            "MRN (Movement Reference Number) must be unique!",
        ),
    ]

    @api.onchange("customs_name")
    def _onchange_customs_name(self):
        if self.customs_name:
            self.move_id.l10n_bg_name = self.customs_name

    @api.onchange("mrn")
    def _onchange_mrn(self):
        # UI feedback; същинската нормализация е в create/write (виж по-долу).
        if self.mrn:
            self.mrn = self.mrn.upper().replace(" ", "") or False

    @api.model
    def _normalize_mrn_vals(self, vals):
        # Нормализирай MRN към главни букви без интервали на ВСЕКИ път (create/
        # write през RPC/import, не само UI onchange). Празен/whitespace резултат
        # → False (NULL): Postgres третира NULL като различни, но два „" се
        # сблъскват в unique(mrn). Кейс-нормализацията пази дедупа реален.
        if "mrn" in vals:
            cleaned = (vals["mrn"] or "").upper().replace(" ", "")
            vals["mrn"] = cleaned or False
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_mrn_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._normalize_mrn_vals(vals)
        return super().write(vals)

    def _customs_aml(self, invoice_id, new_entry_id, map_id):
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
        tax_ids = account_id.tax_ids.filtered(
            lambda tax: tax.type_tax_use == "purchase"
        )
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
                    "l10n_bg_customs_invoice_id": invoice_id.id,
                    "tax_ids": [Command.set(tax_ids.ids)],
                }
            )
        ]
        return aml_vals_list

    def _customs_vals(self, move_id):
        return {
            "move_id": move_id.id,
            "customs_name": move_id.l10n_bg_name,
            "customs_date": move_id.invoice_date,
        }
