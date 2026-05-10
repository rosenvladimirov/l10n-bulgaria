# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
import re
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round

_logger = logging.getLogger(__name__)

INFOPAY_NUMBER_REGEX = re.compile(r"^[0-9]{10}$")
INFOPAY_SUPPORTED_CURRENCIES = ("BGN", "EUR", "USD", "GBP", "CHF")
INFOPAY_DEC = 2  # InfoPay rounds amounts to 2 decimals


class AccountMove(models.Model):
    _inherit = "account.move"

    # ── InfoPay state tracking ────────────────────────────────────────

    l10n_bg_infopay_state = fields.Selection(
        [
            ("not_sent", "Not sent"),
            ("sent", "Sent"),
            ("error", "Error"),
        ],
        string="InfoPay state",
        default="not_sent",
        copy=False,
        tracking=True,
    )
    l10n_bg_infopay_invoice_id = fields.Char(
        string="InfoPay Invoice ID",
        copy=False,
        readonly=True,
        help="GUID returned by POST /api/invoices.  Acts as the only handle "
             "to the document inside InfoPay (no GET / cancel endpoint).",
    )
    l10n_bg_infopay_sent_at = fields.Datetime(
        string="InfoPay Sent At", copy=False, readonly=True,
    )
    l10n_bg_infopay_error = fields.Text(
        string="InfoPay Last Error", copy=False,
    )

    # ── computed flags for UI ─────────────────────────────────────────

    l10n_bg_infopay_can_issue = fields.Boolean(
        compute="_compute_l10n_bg_infopay_can_issue",
    )

    @api.depends(
        "state",
        "move_type",
        "journal_id.l10n_bg_infopay_invoice_enabled",
        "l10n_bg_infopay_state",
    )
    def _compute_l10n_bg_infopay_can_issue(self):
        for move in self:
            move.l10n_bg_infopay_can_issue = (
                move.state == "posted"
                and move.move_type in ("out_invoice", "out_refund")
                and move.journal_id.l10n_bg_infopay_invoice_enabled
                and move.l10n_bg_infopay_state != "sent"
            )

    # ── public action (button on the form) ────────────────────────────

    def action_l10n_bg_infopay_issue(self):
        """Submit this invoice to InfoPay.

        Synchronous: returns when the API has accepted (or rejected) the
        request.  On success the move is marked 'sent' with the returned
        ``invoiceId``; on failure the error is captured for the operator
        to read on the form.
        """
        for move in self:
            if not move.l10n_bg_infopay_can_issue:
                raise UserError(_(
                    "Invoice %s cannot be issued via InfoPay (state=%s, "
                    "infopay_state=%s).",
                    move.display_name, move.state, move.l10n_bg_infopay_state,
                ))
            move._l10n_bg_infopay_issue()
        return True

    # ── core submit ───────────────────────────────────────────────────

    def _l10n_bg_infopay_issue(self):
        self.ensure_one()
        provider = self.env["infopay.provider"]
        payload = self._l10n_bg_infopay_build_payload()

        session = provider._create_session(self.company_id)
        try:
            try:
                result = provider._create_invoice(session, payload)
            except UserError as exc:
                self.write({
                    "l10n_bg_infopay_state": "error",
                    "l10n_bg_infopay_error": str(exc),
                })
                self.message_post(
                    body=_("InfoPay invoice issuance failed: %s", exc),
                )
                return False
        finally:
            provider._close_session(session)

        invoice_id = result.get("invoiceId") or result.get("InvoiceId")
        self.write({
            "l10n_bg_infopay_state": "sent",
            "l10n_bg_infopay_invoice_id": invoice_id,
            "l10n_bg_infopay_sent_at": fields.Datetime.now(),
            "l10n_bg_infopay_error": False,
        })
        self.message_post(
            body=_(
                "Invoice issued via InfoPay.<br/>InfoPay ID: <code>%s</code>",
                invoice_id or "?",
            ),
        )
        return True

    # ── payload builder ───────────────────────────────────────────────

    def _l10n_bg_infopay_build_payload(self):
        """Construct the ``InvoiceCreateRequest`` JSON body.

        Validates Bulgarian / InfoPay-specific constraints up-front so the
        operator sees a Python ValidationError instead of an HTTP 400 from
        the server (faster feedback, no pollution of the InfoPay log).
        """
        self.ensure_one()
        journal = self.journal_id
        if not journal.l10n_bg_infopay_number_series_id:
            raise ValidationError(_(
                "Journal '%s' has no InfoPay number series configured.",
                journal.name,
            ))

        currency_code = (self.currency_id.name or "").upper()
        if currency_code not in INFOPAY_SUPPORTED_CURRENCIES:
            raise ValidationError(_(
                "InfoPay does not support currency %s — supported: %s.",
                currency_code, ", ".join(INFOPAY_SUPPORTED_CURRENCIES),
            ))

        # Language: derive from the customer's preferred language; only
        # InfoPay PDF static text is affected.  Anything starting with
        # "bg" → BG; everything else → EN.
        partner_lang = (self.partner_id.lang or "").lower()
        language = "BG" if partner_lang.startswith("bg") else "EN"

        return {
            "number": self._l10n_bg_infopay_extract_invoice_number(),
            "numberSeriesId": journal.l10n_bg_infopay_number_series_id,
            "language": language,
            "currency": currency_code,
            "invoiceDate": fields.Date.to_string(self.invoice_date or self.date),
            "taxEventDate": fields.Date.to_string(
                self.delivery_date or self.invoice_date or self.date
            ),
            "customer": self._l10n_bg_infopay_customer_dict(),
            "content": self._l10n_bg_infopay_content_dict(),
            "paymentDetails": self._l10n_bg_infopay_payment_details_dict(),
            "additionalInformation": self._l10n_bg_infopay_additional_info_dict(),
        }

    # ── number ────────────────────────────────────────────────────────

    def _l10n_bg_infopay_extract_invoice_number(self):
        """Build the 10-digit InfoPay invoice number for this move.

        InfoPay regex is ``^[0-9]{10}$`` — strict, leading zeros.

        Primary source: ``move.l10n_bg_document_number`` (computed
        field provided by ``l10n_bg_config.account_move``).  That
        field already strips the journal/year prefix (``INV/2026/00001
        → 0000000001``) and matches Bulgarian VAT regulation Art. 78
        on sequential invoice numbering.  Using it keeps the
        InfoPay-side number identical to the printed receipt and to
        the Odoo move.name — auditable round-trip.

        Fallback: ``str(move.id).zfill(10)``.  Only triggered when
        ``l10n_bg_document_number`` is absent (state=draft, or the
        l10n_bg_config field empty for some legacy reason).  Move id
        is a database PK and so is unique within the company — but
        not human-readable.  Logged at WARNING when the fallback
        fires so an operator can check why the canonical БГ number
        wasn't populated.

        Two-different-journals-with-overlapping-sequences edge case:
        breaks Bulgarian VAT regardless of InfoPay (Art. 78 forbids
        two invoices with the same number per company).  We trust
        the upstream l10n_bg_config check + per-company sequence
        configuration — InfoPay is not the right place to police it.
        """
        self.ensure_one()
        candidate = self.l10n_bg_document_number or ""
        if not candidate or not INFOPAY_NUMBER_REGEX.match(candidate):
            if not self.id:
                raise ValidationError(_(
                    "Invoice %s has not been saved yet; cannot derive "
                    "an InfoPay number.", self.display_name,
                ))
            if self.id >= 10 ** 10:
                raise ValidationError(_(
                    "Invoice id %s exceeds 10 digits — InfoPay number "
                    "cannot be derived without overflow.  Configure "
                    "l10n_bg_document_number on the move or switch to a "
                    "dedicated InfoPay sequence.", self.id,
                ))
            fallback = str(self.id).zfill(10)
            _logger.warning(
                "InfoPay number for move %s (id=%s) falling back to "
                "move.id (%s) — l10n_bg_document_number was %r.  Check "
                "the journal sequence + l10n_bg_config setup.",
                self.display_name, self.id, fallback, candidate,
            )
            candidate = fallback
        if not INFOPAY_NUMBER_REGEX.match(candidate):
            raise ValidationError(_(
                "Derived InfoPay number %s for move %s does not match "
                "the required regex.", candidate, self.display_name,
            ))
        return candidate

    # ── customer block ────────────────────────────────────────────────

    def _l10n_bg_infopay_customer_dict(self):
        partner = self.partner_id.commercial_partner_id
        if not partner:
            raise ValidationError(_(
                "Invoice %s has no customer set.", self.display_name,
            ))

        # identificationNumber covers EIK / ЕГН / ЛНЧ — fall back to vat
        # if BG-specific fields are not populated.  Real-world БГ
        # localizations carry l10n_bg_uic on res.partner; gracefully
        # accept that or any free-text id.
        ident = (
            getattr(partner, "l10n_bg_uic", False)
            or partner.vat
            or partner.ref
        )
        if not ident:
            raise ValidationError(_(
                "Customer %s has no identification number (EIK / ЕГН / ЛНЧ "
                "or VAT) set — InfoPay requires one.", partner.display_name,
            ))

        # Strip leading "BG" from a VAT used as ident, but keep the full
        # value (with prefix) on vatId for VAT-registered partners.
        ident_clean = ident
        if ident_clean.upper().startswith("BG"):
            ident_clean = ident_clean[2:]

        addr = {
            "country": (partner.country_id.code or "BG").upper(),
            "city": (partner.city or "")[:100],
            "address": ", ".join(filter(None, [partner.street, partner.street2]))[:200],
        }
        if not addr["city"] or not addr["address"]:
            raise ValidationError(_(
                "Customer %s is missing city or street — both are required "
                "by InfoPay.", partner.display_name,
            ))

        cust = {
            "identificationNumber": ident_clean,
            "name": partner.name[:100],
            "address": addr,
        }
        if partner.vat:
            cust["vatId"] = partner.vat
        if partner.email:
            cust["email"] = partner.email
        return cust

    # ── content (with VAT) ────────────────────────────────────────────

    def _l10n_bg_infopay_content_dict(self):
        """Build ``contentWithVAT`` with items + group totals.

        InfoPay validates arithmetic strictly — round each line to 2
        decimals BEFORE summing, then re-sum to derive group + grand
        totals.  Any drift > 0.01 triggers HTTP 400.
        """
        self.ensure_one()
        items = []
        groups = defaultdict(lambda: {
            "amount": 0.0, "vatAmount": 0.0, "amountVATIncluded": 0.0,
        })
        is_refund = self.move_type == "out_refund"
        sign = -1 if is_refund else 1

        for line in self.invoice_line_ids.filtered(
            lambda l: l.display_type == "product"
        ):
            qty = float_round(line.quantity, precision_digits=4)
            unit_price = float_round(line.price_unit, precision_digits=INFOPAY_DEC)
            amount = float_round(qty * unit_price, precision_digits=INFOPAY_DEC)

            tax = line.tax_ids[:1]
            if tax and abs(tax.amount) > 0.0001:
                vat_rate = {"@vatRateType": "NonZeroVAT", "percentage": float(tax.amount)}
            else:
                # 0% or no tax — InfoPay needs a free-text reason
                vat_rate = {
                    "@vatRateType": "ZeroVAT",
                    "reason": (
                        getattr(tax, "description", False)
                        or _("Освободена доставка / 0%% VAT")
                    ),
                }

            vat_amount = float_round(
                amount * (vat_rate.get("percentage", 0.0) / 100.0),
                precision_digits=INFOPAY_DEC,
            )
            amount_incl = float_round(amount + vat_amount, precision_digits=INFOPAY_DEC)

            items.append({
                "name": (line.product_id.display_name or line.name or "")[:200],
                "description": (line.name or "")[:500],
                "measureUnit": (line.product_uom_id.name or "бр.")[:20],
                "quantity": str(qty),
                "unitPrice": str(unit_price),
                "vatRate": vat_rate,
                "amount": str(sign * amount),
                "vatAmount": str(sign * vat_amount),
                "amountVATIncluded": str(sign * amount_incl),
            })

            # Group key: percentage for NonZeroVAT, "0" for ZeroVAT
            key = vat_rate.get("percentage", "0")
            g = groups[key]
            g["amount"] += sign * amount
            g["vatAmount"] += sign * vat_amount
            g["amountVATIncluded"] += sign * amount_incl

        if not items:
            raise ValidationError(_(
                "Invoice %s has no product lines to send to InfoPay.",
                self.display_name,
            ))

        amounts_by_group = []
        for key, totals in groups.items():
            row = {
                "amount": str(float_round(totals["amount"], precision_digits=INFOPAY_DEC)),
                "vatAmount": str(float_round(totals["vatAmount"], precision_digits=INFOPAY_DEC)),
                "amountVATIncluded": str(float_round(
                    totals["amountVATIncluded"], precision_digits=INFOPAY_DEC,
                )),
            }
            if key == "0":
                row["vatRate"] = {"@vatRateType": "ZeroVAT",
                                  "reason": _("Освободена доставка / 0%% VAT")}
            else:
                row["vatRate"] = {"@vatRateType": "NonZeroVAT", "percentage": float(key)}
            amounts_by_group.append(row)

        total = sum(g["amountVATIncluded"] for g in groups.values())
        net = sum(g["amount"] for g in groups.values())
        vat = sum(g["vatAmount"] for g in groups.values())

        return {
            "@contentType": "contentWithVAT",
            "items": items,
            "amountsByVatGroup": amounts_by_group,
            "amountPayable": {
                "amount": str(float_round(net, precision_digits=INFOPAY_DEC)),
                "vatAmount": str(float_round(vat, precision_digits=INFOPAY_DEC)),
                "amountVATIncluded": str(float_round(total, precision_digits=INFOPAY_DEC)),
            },
        }

    # ── payment details ───────────────────────────────────────────────

    def _l10n_bg_infopay_payment_details_dict(self):
        """Build ``paymentDetails`` block.

        Default payment type is ``bankTransfer`` — it covers the bulk of
        B2B InfoPay issuances.  IBAN fallback chain:

            1. ``move.partner_bank_id`` (set on the invoice itself)
            2. ``journal.bank_account_id``
            3. company's first ``res.partner.bank``

        If a caller needs cash / card / other, they pass it via context
        ``self.with_context(l10n_bg_infopay_payment_type=...)`` before
        invoking ``action_l10n_bg_infopay_issue``.  Not a journal-level
        field because per-move override is the realistic pattern.
        """
        self.ensure_one()
        ctx_method = self.env.context.get("l10n_bg_infopay_payment_type")
        method = ctx_method or "bankTransfer"
        block = {"paymentMethod": {"@paymentType": method}}

        if method == "bankTransfer":
            # IBAN fallback chain — most-specific first.  Defensive
            # null-check on bank_id is required: a res.partner.bank
            # record can exist without a linked res.bank (rare but
            # legal in Odoo), and `False.name` raises AttributeError.
            bank_acc = (
                self.partner_bank_id
                or self.journal_id.bank_account_id
                or self.company_id.bank_ids[:1]
            )
            iban = bank_acc.acc_number if bank_acc else None
            if iban:
                if bank_acc and bank_acc.bank_id:
                    bank_name = bank_acc.bank_id.name or self.company_id.name
                else:
                    bank_name = self.company_id.name
                block["paymentMethod"]["accounts"] = [{
                    "bank": (bank_name or "")[:100],
                    "iban": iban.replace(" ", ""),
                    "currency": (self.currency_id.name or "BGN").upper(),
                }]

        if self.invoice_date_due:
            block["dueDate"] = fields.Date.to_string(self.invoice_date_due)
        if self.payment_reference:
            block["notes"] = self.payment_reference[:500]
        return block

    # ── additional information ────────────────────────────────────────

    def _l10n_bg_infopay_additional_info_dict(self):
        self.ensure_one()
        info = {}
        # Free-text notes — concatenate narration + ref where useful.
        bits = []
        if self.ref:
            bits.append(self.ref)
        if self.narration:
            from odoo.tools import html2plaintext
            bits.append(html2plaintext(self.narration))
        if bits:
            info["notes"] = " | ".join(bits)[:500]
        if self.invoice_origin:
            info["orderId"] = self.invoice_origin[:100]
        return info or None
