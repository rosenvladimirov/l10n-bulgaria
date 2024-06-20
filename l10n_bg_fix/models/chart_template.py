#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.base.models.res_lang import intersperse
from odoo.addons.l10n_bg_config.models.account_move import get_doc_type, get_type_vat

_logger = logging.getLogger(__name__)


def get_invoice_type():
    return [
        ("out_invoice", _("Customer Invoice")),
        ("out_refund", _("Customer Credit Note")),
        ("out_debit_note", _("Customer Debit Note")),
        ("out_receipt", _("Sales Receipt")),
        ("out_receipt_invoice", _("Sales Receipt-Invoice")),
        ("in_invoice", _("Vendor Bill")),
        ("in_refund", _("Vendor Credit Note")),
        ("in_debit_note", _("Vendor Debit Note")),
        ("in_receipt_invoice", _("Purchase Receipt-Invoice")),
        ("entry", _("Account Entry")),
    ]


class AccountFiscalPositionTemplate(models.Model):
    _inherit = "account.fiscal.position.template"

    type_ids = fields.One2many(
        "account.fiscal.position.type.template",
        "position_id",
        string="Type Mapping",
        copy=True,
    )


class AccountTypeTemplate(models.Model):
    _name = "account.fiscal.position.type.template"
    _description = "Type Mapping Template of Fiscal Position"
    _order = "position_id"

    position_id = fields.Many2one(
        "account.fiscal.position.template",
        string="Fiscal Position Template",
        required=True,
        ondelete="cascade",
    )
    position_dest_id = fields.Many2one(
        "account.fiscal.position.template", string="Replacement fiscal position"
    )
    invoice_type = fields.Selection(
        selection=get_invoice_type(), string="Invoice type", index=True, copy=False
    )
    l10n_bg_type_vat = fields.Selection(
        selection=get_type_vat(),
        string="Type of numbering",
        default="standard",
        copy=False,
        index=True,
    )
    l10n_bg_doc_type = fields.Selection(
        selection=get_doc_type(),
        string="Vat type document",
        default="01",
        copy=False,
        index=True,
    )
    l10n_bg_narration = fields.Char("Narration for audit report", translate=True)
    account_id = fields.Many2one("account.account", string="Account")
    factor_percent = fields.Float(
        string="%",
        default=100,
        help="Factor to apply on the account move lines generated from this distribution line, in percents",
    )
    new_account_entry = fields.Boolean("Create new account entry")
