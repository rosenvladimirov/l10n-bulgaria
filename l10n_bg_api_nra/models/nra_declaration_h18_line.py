"""
Order + article + refund line models за H-18 audit declaration
(Приложение №38 към Наредба Н-18/2006).

Trois modela: order line (orderenum), article sub-line (artenum),
refund line (rorderenum). Те носят 1:1 структурата на XSD-то и
могат да се edit-ват ръчно от UI преди XML generation.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .nra_declaration_h18_eshop import (
    PAYMENT_METHOD_SELECTION,
    REFUND_PAYMENT_SELECTION,
)


class NraDeclarationH18Line(models.Model):
    _name = "nra.declaration.h18.line"
    _description = "H-18 Audit File — Order Line (orderenum)"
    _order = "ord_d, id"

    declaration_id = fields.Many2one(
        "nra.declaration",
        string="Declaration",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # XSD: ord_n — string max 300; уникален номер на поръчката от
    # софтуера на е-магазина.
    ord_n = fields.Char(
        string="Order number",
        size=300,
        required=True,
        help="Unique order number assigned by the e-shop software.",
    )
    ord_d = fields.Date(
        string="Order date",
        required=True,
    )
    # XSD: doc_n — integer; номер на документа по чл. 52с, ал. 1, т. 1
    # (фактура / стокова разписка)
    doc_n = fields.Integer(
        string="Document #",
        required=True,
        help="Number of the document under Art. 52s, par. 1, item 1 "
        "(invoice / delivery note).",
    )
    doc_date = fields.Date(
        string="Document date",
        required=True,
    )

    # Totals (decimal — 2 fractional digits)
    ord_total1 = fields.Float(
        string="Total without VAT (BGN)",
        digits=(12, 2),
        required=True,
        help="Total of the requested goods/services without VAT.",
    )
    ord_disc = fields.Float(
        string="Discount (BGN)",
        digits=(12, 2),
        default=0.0,
    )
    ord_vat = fields.Float(
        string="VAT amount (BGN)",
        digits=(12, 2),
        required=True,
    )
    ord_total2 = fields.Float(
        string="Total delivered with VAT (BGN)",
        digits=(12, 2),
        required=True,
        help="Total of the delivered/dispatched goods/services with VAT.",
    )

    paym = fields.Selection(
        selection=PAYMENT_METHOD_SELECTION,
        string="Payment method",
        required=True,
        default="1",
    )
    pos_n = fields.Char(
        string="POS / Terminal #",
        size=200,
        help="POS or terminal number (optional).",
    )
    trans_n = fields.Char(
        string="Transaction #",
        size=200,
        help="Unique transaction number from the payment provider (optional).",
    )
    proc_id = fields.Char(
        string="Processor ID",
        size=200,
        help="Identifier of the payment service provider (optional).",
    )

    art_line_ids = fields.One2many(
        "nra.declaration.h18.line.art",
        "line_id",
        string="Articles",
    )
    art_count = fields.Integer(
        string="Articles count",
        compute="_compute_art_count",
    )

    @api.depends("art_line_ids")
    def _compute_art_count(self):
        for rec in self:
            rec.art_count = len(rec.art_line_ids)

    @api.constrains("ord_total2", "art_line_ids")
    def _check_totals(self):
        # Tolerance 1 cent — XML uses 2-decimal rounding.
        for rec in self:
            if rec.art_line_ids:
                art_sum = sum(rec.art_line_ids.mapped("art_sum"))
                if abs(art_sum - rec.ord_total2) > 0.01:
                    raise ValidationError(_(
                        "Order %s: sum of article totals (%.2f) differs from "
                        "ord_total2 (%.2f).") % (
                            rec.ord_n, art_sum, rec.ord_total2))


class NraDeclarationH18LineArt(models.Model):
    _name = "nra.declaration.h18.line.art"
    _description = "H-18 Audit File — Article (artenum)"

    line_id = fields.Many2one(
        "nra.declaration.h18.line",
        string="Order line",
        required=True,
        ondelete="cascade",
        index=True,
    )
    art_name = fields.Char(
        string="Article name",
        size=200,
        required=True,
    )
    art_quant = fields.Float(
        string="Quantity",
        digits=(12, 2),
        required=True,
    )
    art_price = fields.Float(
        string="Unit price w/o VAT (BGN)",
        digits=(12, 2),
        required=True,
    )
    art_vat_rate = fields.Integer(
        string="VAT rate (%)",
        required=True,
        default=20,
    )
    art_vat = fields.Float(
        string="VAT amount (BGN)",
        digits=(12, 2),
        required=True,
    )
    art_sum = fields.Float(
        string="Total with VAT (BGN)",
        digits=(12, 2),
        required=True,
    )

    @api.constrains("art_vat_rate")
    def _check_vat_rate(self):
        for rec in self:
            if not (0 <= rec.art_vat_rate <= 100):
                raise ValidationError(_(
                    "VAT rate must be between 0 and 100 (got %s).") %
                    rec.art_vat_rate)


class NraDeclarationH18Refund(models.Model):
    _name = "nra.declaration.h18.refund"
    _description = "H-18 Audit File — Refund Line (rorderenum)"
    _order = "r_date, id"

    declaration_id = fields.Many2one(
        "nra.declaration",
        string="Declaration",
        required=True,
        ondelete="cascade",
        index=True,
    )
    r_ord_n = fields.Char(
        string="Refund / order #",
        size=300,
        required=True,
        help="Refund number (or unique number of the credit document and "
        "the original order).",
    )
    r_amount = fields.Float(
        string="Refunded amount (BGN)",
        digits=(12, 2),
        required=True,
    )
    r_date = fields.Date(
        string="Refund date",
        required=True,
    )
    r_paym = fields.Selection(
        selection=REFUND_PAYMENT_SELECTION,
        string="Refund payment method",
        required=True,
        default="1",
    )
