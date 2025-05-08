# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import Command, _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # ---------------
    # PROTOCOL FIELDS
    # ---------------
    l10n_bg_protocol_number = fields.Char(
        "Technical Protocol number", copy=False
    )
    l10n_bg_protocol_date = fields.Date(
        "Technical Protocol date", copy=False, default=fields.Date.today()
    )
    l10n_bg_protocol_move_id = fields.Many2one(
        "account.move.bg.protocol",
        "Protocol",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    # --------------------------
    # Private credit reverse VAT
    # --------------------------
    l10n_bg_private_number = fields.Char(
        "Technical Protocol number", copy=False
    )
    l10n_bg_private_vat_date = fields.Date(
        "Technical Self signed private VAT date",
        copy=False,
        default=fields.Date.today(),
    )
    l10n_bg_private_move_id = fields.Many2one(
        "account.move.bg.private",
        "Self signed Private VAT",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    l10n_bg_private_move_ids = fields.Many2many(
        "account.move.bg.private",
        "invoices_private_vat_rel",
        "invoice_id",
        "private_id",
        string="Used invoices for private vat",
        check_company=True,
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    # --------------------------
    # Customs moves VAT
    # --------------------------
    l10n_bg_customs_number = fields.Char(
        "Technical Protocol number", copy=False
    )
    l10n_bg_customs_vat_date = fields.Date(
        "Technical Self signed private VAT date",
        copy=False,
        default=fields.Date.today(),
    )
    l10n_bg_customs_move_id = fields.Many2one(
        "account.move.bg.customs",
        "Self signed Private VAT",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    l10n_bg_customs_move_ids = fields.Many2many(
        "account.move.bg.customs",
        "invoices_customs_vat_rel",
        "invoice_id",
        "customs_id",
        string="Used invoices for private vat",
        check_company=True,
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
