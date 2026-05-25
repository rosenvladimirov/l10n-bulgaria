# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Service for the storno Phase 2 lookup + refund-printed flow.

Companion to `shift_sync_service.py`. Holds the per-pos.order lookup
logic that the controller endpoint calls into:

  * `lookup_by_id(order_id)` — find pos.order by Odoo ID, validate
    state, return the dict shape from
    `anchor_bluecash_storno_phase2_contract.md` §1.
  * `lookup_by_uns(uns)` — same but indexed via `l10n_bg_uns`
    (cross-device storno per anchor §"checklist" bullet 3).
  * `register_refund_printed(order_id, storno_uns, ...)` — invoked
    after Android prints the storno; creates a refund pos.order
    linked to the original and stores the storno UNS on it.

Validation rules (per anchor §2):
  * order.state ∈ {paid, done, invoiced}     → OK
  * already refunded fully                   → 409 Conflict
  * partial refund coverage check            → Phase 2.1 (TODO; for
    now we allow re-print and let the cashier reconcile)
"""

from __future__ import annotations

import logging

from odoo import SUPERUSER_ID, _, api, fields, models

_logger = logging.getLogger(__name__)


# Slot → external_kind reverse — mirrors shift_sync_service map; kept
# in sync explicitly to avoid coupling the two services.
_SLOT_BY_KIND = {
    "cash": 0,
    "card": 1,
    "other": 3,
    "voucher": 5,
}


def _slot_for_method(method) -> int:
    kind = (method.l10n_bg_external_kind or "").lower()
    return _SLOT_BY_KIND.get(kind, 0)


# Reverse VAT slot → letter map (matches l10n_bg_tax_admin / shift_sync).
_VAT_SLOT_LETTER = {1: "А", 2: "Б", 3: "В", 4: "Г",
                    5: "Д", 6: "Е", 7: "Ж", 8: "З"}


def _vat_letter_for_line(line) -> str:
    """Best-effort: pick the first tax group letter from the line's
    tax_ids; fall back to `Б` (standard 20% in BG)."""
    for tax in line.tax_ids:
        # Try several conventions used across l10n_bg revisions:
        # tax.l10n_bg_external_slot int → mapped letter
        slot = getattr(tax, "l10n_bg_external_slot", 0)
        if slot:
            letter = _VAT_SLOT_LETTER.get(int(slot))
            if letter:
                return letter
        # tax.tax_group_id.l10n_bg_letter direct
        letter = getattr(getattr(tax, "tax_group_id", False),
                         "l10n_bg_letter", "")
        if letter:
            return letter[:1]
    return "Б"


class L10nBgFpPosOrderStorno(models.TransientModel):
    _name = "l10n.bg.erp.net.fp.pos.order.storno"
    _description = "BlueCash storno Phase 2 lookup service"

    # ─── lookup entrypoints ─────────────────────────────────────────

    @api.model
    def lookup_by_id(self, order_id: int) -> dict:
        order = self.env["pos.order"].sudo().browse(order_id)
        if not order.exists():
            return {"error": "pos.order not found", "_http_status": 404}
        return self._build_payload(order)

    @api.model
    def lookup_by_uns(self, uns: str) -> dict:
        if not uns:
            return {"error": "UNS required", "_http_status": 400}
        order = self.env["pos.order"].sudo().search(
            [("l10n_bg_uns", "=", uns)], limit=1)
        if not order:
            return {"error": f"pos.order with UNS {uns!r} not found",
                    "_http_status": 404}
        return self._build_payload(order)

    # ─── payload builder ────────────────────────────────────────────

    @api.model
    def _build_payload(self, order) -> dict:
        # Refund-coverage check (anchor §2): if order already has a
        # linked refund whose UNS we know, return 409 with details.
        # Phase 2.0: a refund order is identified by a sibling pos.order
        # whose pos_reference starts with FP/D<dev>/R + this order's
        # receipt_number — same convention as shift_sync._upsert_refund.
        existing_refund = self.env["pos.order"].sudo().search([
            ("pos_reference", "=like",
             f"FP/D%/R{(order.pos_reference or '').split('/')[-1]}"),
            ("id", "!=", order.id),
        ], limit=1)
        if existing_refund:
            return {
                "error": "Order already refunded",
                "refund_uns": existing_refund.l10n_bg_uns or "",
                "refund_order_id": existing_refund.id,
                "_http_status": 409,
            }
        if order.state not in ("paid", "done", "invoiced"):
            return {
                "error": (f"pos.order #{order.id} state is "
                          f"{order.state!r}, expected paid/done/invoiced"),
                "_http_status": 409,
            }

        # Plu lookup per line (reverse: product → fiscal.plu).
        Plu = self.env["l10n.bg.fiscal.plu"]
        product_to_plu: dict[int, int] = {}
        for line in order.lines:
            if line.product_id.id in product_to_plu:
                continue
            plu = Plu.search([
                ("product_ids", "in", line.product_id.id),
                ("company_id", "=", order.company_id.id),
                ("active", "=", True),
            ], limit=1)
            if plu:
                product_to_plu[line.product_id.id] = plu.plu_number

        lines_out = []
        for line in order.lines:
            plu_num = product_to_plu.get(line.product_id.id, 0)
            lines_out.append({
                "plu": plu_num,
                "qty": float(line.qty),
                "unit_price": float(line.price_unit),
                "vat_letter": _vat_letter_for_line(line),
            })

        payments_out = []
        for pay in order.payment_ids:
            payments_out.append({
                "fiscal_slot": _slot_for_method(pay.payment_method_id),
                "amount": float(pay.amount),
            })

        # Doc number — Phase 1 store-ваме само в pos_reference като
        # `FP/D<dev_id>/<receipt_number>`. Извличаме trailing-а.
        doc_number = ""
        if order.pos_reference and "/" in order.pos_reference:
            doc_number = order.pos_reference.split("/")[-1]

        # Till number — best-effort от config_id; default 1.
        till_number = int(
            getattr(order.config_id, "l10n_bg_till_number", 0) or 1)

        return {
            "uns": order.l10n_bg_uns or "",
            "doc_number": doc_number,
            "issued_at": fields.Datetime.to_string(order.date_order)
                         if order.date_order else "",
            "device_serial": order.l10n_bg_device_serial or "",
            "till_number": till_number,
            "lines": lines_out,
            "payments": payments_out,
        }

    # ─── refund-printed sink ────────────────────────────────────────

    @api.model
    def register_refund_printed(
        self, order_id: int,
        storno_uns: str = "",
        storno_doc_number: str = "",
        device_serial: str = "",
    ) -> dict:
        """Android-emitted notification: storno printed, create refund."""
        if not storno_uns:
            return {"ok": False, "error": "storno_uns required",
                    "_http_status": 400}
        original = self.env["pos.order"].sudo().browse(order_id)
        if not original.exists():
            return {"ok": False,
                    "error": f"original pos.order #{order_id} not found",
                    "_http_status": 404}
        # Idempotency: ако вече има refund с тоя UNS — върни го.
        existing = self.env["pos.order"].sudo().search(
            [("l10n_bg_uns", "=", storno_uns)], limit=1)
        if existing:
            return {"ok": True, "refund_order_id": existing.id,
                    "warnings": ["refund already exists for this UNS"]}
        # Create minimal refund pos.order (headers only — Android already
        # printed the device-side; we mirror the totals).
        refund_vals = {
            "session_id": original.session_id.id,
            "company_id": original.company_id.id,
            "pos_reference": f"FP/D{0}/R{storno_doc_number or storno_uns}",
            "amount_tax": -original.amount_tax,
            "amount_total": -original.amount_total,
            "amount_paid": -original.amount_paid,
            "amount_return": 0.0,
            "l10n_bg_uns": storno_uns,
            "l10n_bg_z_report_number": original.l10n_bg_z_report_number or "",
            "l10n_bg_device_serial": device_serial
                                     or original.l10n_bg_device_serial or "",
            "l10n_bg_fiscal_day_number":
                original.l10n_bg_fiscal_day_number,
        }
        refund = self.env["pos.order"].sudo().with_user(
            SUPERUSER_ID).create(refund_vals)
        return {"ok": True, "refund_order_id": refund.id, "warnings": []}
