# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Service for BlueCash shift-close payloads.

Receives a JSON payload from a paired proxy after a Z-report close on
an Android-side device. Performs an idempotent upsert into Odoo:

  * find `pos.session` by `odoo_session_id`
  * find `fiscal.printer.device` by `l10n_bg_device_serial`
  * upsert each receipt as a `pos.order` keyed by `l10n_bg_uns`
  * for `is_storno=True` receipts: find the original order via
    `original_uns` and create a refund order (negative qty lines)
  * post cash movements to `account.bank.statement.line`
  * mark the session as closed

Payload shape per `anchor_bluecash_shift_sync_contract.md`.

The service is fully idempotent: same payload posted N times produces
exactly one set of records (per-receipt UNS uniqueness + session-level
totals match check).

Special return key `_http_status` lets the controller emit 409 Conflict
when the session is already closed AND totals don't match.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from odoo import SUPERUSER_ID, _, api, fields, models

_logger = logging.getLogger(__name__)


# Fiscal payment slot → external_kind. Empirically verified mapping
# from FP-700MX/BC-50MX 6-slot PM layout (виж
# `odoo_erpnet_fp/server/adapters/payment_type.py:_DATECS_PM_DEFAULT`):
#
#   Slot │ Label    │ external_kind
#   ─────┼──────────┼──────────────
#     0  │ В БРОЙ   │ cash
#     1  │ КРЕДИТ   │ card
#     2  │ ДЕБ.КАРТА│ card (debit card semantically still "card")
#     3  │ ЧЕК      │ other (no check kind на Odoo страна)
#     4  │ ВАУЧЕР   │ voucher
#     5  │ КУПОН    │ voucher (coupon ≈ voucher семантично)
_SLOT_TO_KIND = {
    0: "cash",
    1: "card",
    2: "card",
    3: "other",
    4: "voucher",
    5: "voucher",
}


def _parse_iso(s: str) -> datetime | None:
    """Best-effort ISO-8601 parse. Връща naive UTC datetime или None."""
    if not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        # Към UTC naive (Odoo пази всичко в UTC без tz).
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt


class L10nBgFpShiftSync(models.TransientModel):
    _name = "l10n.bg.erp.net.fp.shift.sync"
    _description = "BlueCash Shift-Close Sync Service"

    # ─── Entry point ────────────────────────────────────────────────

    @api.model
    def apply(self, payload: dict, dry_run: bool = False) -> dict:
        """Idempotent entrypoint.

        Returns a dict matching the anchor contract:
            {status, odoo_session_id, odoo_orders_created,
             odoo_refunds_created, warnings: []}
        plus optional `_http_status` (popped by controller before
        emitting JSON).
        """
        warnings: list[str] = []

        # ── 1. Validate payload shape ────────────────────────────────
        try:
            device_serial = str(payload["device_serial"]).strip()
            odoo_session_id = int(payload["odoo_session_id"])
            fiscal_day_number = int(payload["fiscal_day_number"])
            z_report_number = str(payload["z_report_number"]).strip()
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"Malformed shift_close payload: {exc}") from exc

        receipts = payload.get("receipts") or []
        cash_movements = payload.get("cash_movements") or []
        totals = payload.get("totals") or {}

        # ── 2. Resolve session + device ──────────────────────────────
        session = self.env["pos.session"].sudo().browse(odoo_session_id)
        if not session.exists():
            return {
                "status": "error",
                "odoo_session_id": odoo_session_id,
                "warnings": [f"pos.session #{odoo_session_id} not found"],
                "_http_status": 404,
            }
        if session.state == "closed":
            # Опитваме се да съпоставим totals; ако не съвпадат —
            # 409 conflict (виж contract §"Odoo-side behaviour" т.1).
            try:
                expected_total = float(totals.get("total_gross") or 0.0)
            except (TypeError, ValueError):
                expected_total = 0.0
            actual_total = sum(session.order_ids.mapped("amount_total"))
            if abs(actual_total - expected_total) > 0.01:
                return {
                    "status": "conflict",
                    "odoo_session_id": odoo_session_id,
                    "warnings": [
                        f"Session already closed; totals mismatch "
                        f"(odoo={actual_total:.2f}, "
                        f"device={expected_total:.2f})"
                    ],
                    "_http_status": 409,
                }

        device = self.env["fiscal.printer.device"].sudo().search(
            [("l10n_bg_device_serial", "=", device_serial)], limit=1)
        if not device:
            warnings.append(
                f"fiscal.printer.device with serial {device_serial!r} "
                f"not found — receipts will be created without device link"
            )

        # ── 3. Pre-build payment-method lookup ───────────────────────
        # Map external_kind → pos.payment.method за config-а на session-а.
        kind_to_method: dict[str, "pos.payment.method"] = {}
        for pm in session.config_id.payment_method_ids:
            k = pm.l10n_bg_external_kind
            if k and k not in kind_to_method:
                kind_to_method[k] = pm
        # Default fallback — първи cash, после която и да е method.
        default_method = (
            kind_to_method.get("cash")
            or session.config_id.payment_method_ids[:1]
        )
        if not default_method:
            warnings.append(
                "No pos.payment.method configured on POS config; "
                "payments will be skipped on imported orders"
            )

        # ── 4. Process receipts ──────────────────────────────────────
        orders_created = 0
        refunds_created = 0
        for rec in receipts:
            try:
                if rec.get("is_storno"):
                    created = self._upsert_refund(
                        session, device, rec, kind_to_method,
                        default_method, warnings, dry_run)
                    if created:
                        refunds_created += 1
                else:
                    created = self._upsert_order(
                        session, device, rec, kind_to_method,
                        default_method, warnings, dry_run)
                    if created:
                        orders_created += 1
            except Exception as exc:  # noqa: BLE001
                _logger.exception(
                    "shift_sync: failed to process receipt %s",
                    rec.get("uns") or rec.get("receipt_number") or "?")
                warnings.append(
                    f"Receipt {rec.get('uns', '?')}: "
                    f"{exc.__class__.__name__}: {exc}"
                )

        # ── 5. Process cash movements ────────────────────────────────
        for mv in cash_movements:
            try:
                self._post_cash_movement(
                    session, device_serial, mv, warnings, dry_run)
            except Exception as exc:  # noqa: BLE001
                _logger.exception("shift_sync: cash movement failed")
                warnings.append(
                    f"Cash movement {mv}: {exc.__class__.__name__}: {exc}"
                )

        # ── 6. Close session ─────────────────────────────────────────
        if not dry_run and session.state != "closed":
            try:
                self._close_session(session, warnings)
            except Exception as exc:  # noqa: BLE001
                _logger.exception("shift_sync: session close failed")
                warnings.append(
                    f"Session close failed: {exc.__class__.__name__}: {exc}"
                )

        if dry_run:
            warnings.insert(0, "dry-run: no records were written")

        return {
            "status": "ok",
            "odoo_session_id": odoo_session_id,
            "odoo_orders_created": orders_created,
            "odoo_refunds_created": refunds_created,
            "warnings": warnings,
        }

    # ─── Receipt upsert ─────────────────────────────────────────────

    def _resolve_payment_method(self, fiscal_slot, kind_to_method,
                                default_method):
        """Map fiscal slot → pos.payment.method. Fallback to default."""
        kind = _SLOT_TO_KIND.get(int(fiscal_slot), "other")
        return kind_to_method.get(kind) or default_method

    def _upsert_order(self, session, device, rec, kind_to_method,
                      default_method, warnings, dry_run):
        """Lookup-or-create pos.order keyed by l10n_bg_uns.

        Returns True if a new record was created, False if dedupe hit.
        """
        uns = (rec.get("uns") or "").strip()
        if not uns:
            warnings.append(
                f"Receipt {rec.get('receipt_number', '?')} has no UNS — "
                f"skipped"
            )
            return False
        # Idempotency lookup — UNS е unique per fiscal device.
        existing = self.env["pos.order"].sudo().search(
            [("l10n_bg_uns", "=", uns)], limit=1)
        if existing:
            # Не плодим — но забелязваме session-link несъответствие.
            if existing.session_id.id != session.id:
                warnings.append(
                    f"Receipt {uns}: already imported under session "
                    f"#{existing.session_id.id} (this payload targets "
                    f"#{session.id}) — kept original"
                )
            return False
        if dry_run:
            warnings.append(
                f"dry-run: would create pos.order for UNS {uns}"
            )
            return True
        # Минимален pos.order — без line items (Phase 1 не парсва
        # individual sold items; идват от device-pull в отделен flow).
        gross = float(rec.get("gross_amount") or 0.0)
        order_vals = {
            "session_id": session.id,
            "company_id": session.company_id.id,
            "pos_reference": f"FP/D{device.id if device else 0}/"
                             f"{rec.get('receipt_number', '?')}",
            "amount_tax": 0.0,
            "amount_total": gross,
            "amount_paid": gross,
            "amount_return": 0.0,
            "l10n_bg_uns": uns,
            "l10n_bg_z_report_number": rec.get("z_report_number")
                                       or "",
            "l10n_bg_device_serial": device.l10n_bg_device_serial
                                     if device else "",
            "l10n_bg_fiscal_day_number": int(
                rec.get("fiscal_day_number") or 0),
        }
        # Payments — една pos.payment per payment item.
        payments_payload = rec.get("payments") or []
        if payments_payload and default_method:
            payment_vals = []
            for p in payments_payload:
                method = self._resolve_payment_method(
                    p.get("fiscal_slot") or 0,
                    kind_to_method, default_method)
                if not method:
                    continue
                payment_vals.append((0, 0, {
                    "amount": float(p.get("amount") or 0.0),
                    "payment_method_id": method.id,
                    "name": _("Imported from device %s",
                              device.l10n_bg_device_serial if device
                              else "?"),
                }))
            if payment_vals:
                order_vals["payment_ids"] = payment_vals
        printed_at = _parse_iso(rec.get("printed_at") or "")
        if printed_at:
            order_vals["date_order"] = fields.Datetime.to_string(printed_at)
        self.env["pos.order"].sudo().create(order_vals)
        return True

    def _upsert_refund(self, session, device, rec, kind_to_method,
                       default_method, warnings, dry_run):
        """Storno receipt → refund pos.order.

        Phase 1: създаваме self-standing refund (negative amount) с
        link към оригинал чрез `l10n_bg_uns` lookup. Ако `original_uns`
        е подаден И намерим съответен pos.order, попълваме
        `l10n_bg_uns` на refund-а със собственото му UNS и добавяме
        warning указващ оригинала.
        """
        own_uns = (rec.get("uns") or "").strip()
        if not own_uns:
            warnings.append(
                f"Storno receipt {rec.get('receipt_number', '?')} "
                f"has no UNS — skipped"
            )
            return False
        existing = self.env["pos.order"].sudo().search(
            [("l10n_bg_uns", "=", own_uns)], limit=1)
        if existing:
            return False  # already imported

        # Look up original за warning trail (Phase 1 — без real link;
        # Phase 2 anchor определя refunded_orders_count flow).
        original_uns = (rec.get("original_uns") or "").strip()
        if original_uns:
            original = self.env["pos.order"].sudo().search(
                [("l10n_bg_uns", "=", original_uns)], limit=1)
            if not original:
                warnings.append(
                    f"Storno {own_uns}: original UNS {original_uns!r} "
                    f"not found in Odoo — refund created standalone"
                )
        if dry_run:
            warnings.append(
                f"dry-run: would create refund pos.order for UNS {own_uns}"
            )
            return True
        gross = -abs(float(rec.get("gross_amount") or 0.0))
        order_vals = {
            "session_id": session.id,
            "company_id": session.company_id.id,
            "pos_reference": f"FP/D{device.id if device else 0}/"
                             f"R{rec.get('receipt_number', '?')}",
            "amount_tax": 0.0,
            "amount_total": gross,
            "amount_paid": gross,
            "amount_return": 0.0,
            "l10n_bg_uns": own_uns,
            "l10n_bg_z_report_number": rec.get("z_report_number") or "",
            "l10n_bg_device_serial": device.l10n_bg_device_serial
                                     if device else "",
            "l10n_bg_fiscal_day_number": int(
                rec.get("fiscal_day_number") or 0),
        }
        payments_payload = rec.get("payments") or []
        if payments_payload and default_method:
            payment_vals = []
            for p in payments_payload:
                method = self._resolve_payment_method(
                    p.get("fiscal_slot") or 0,
                    kind_to_method, default_method)
                if not method:
                    continue
                payment_vals.append((0, 0, {
                    "amount": -abs(float(p.get("amount") or 0.0)),
                    "payment_method_id": method.id,
                    "name": _("Refund from device %s",
                              device.l10n_bg_device_serial if device
                              else "?"),
                }))
            if payment_vals:
                order_vals["payment_ids"] = payment_vals
        printed_at = _parse_iso(rec.get("printed_at") or "")
        if printed_at:
            order_vals["date_order"] = fields.Datetime.to_string(printed_at)
        self.env["pos.order"].sudo().create(order_vals)
        return True

    # ─── Cash movements ─────────────────────────────────────────────

    def _post_cash_movement(self, session, device_serial, mv,
                            warnings, dry_run):
        """Post cash IN/OUT to account.bank.statement.line.

        Dedupe via `payment_ref` LIKE 'BlueCash/<serial>/<iso_ts>' +
        ±2 s tolerance window (виж contract §Cash movement key).
        """
        occurred_at = _parse_iso(mv.get("occurred_at") or "")
        if occurred_at is None:
            warnings.append(
                f"Cash movement with invalid timestamp "
                f"{mv.get('occurred_at')!r} — skipped"
            )
            return
        direction = (mv.get("direction") or "").upper()
        if direction not in ("IN", "OUT"):
            warnings.append(
                f"Cash movement with invalid direction "
                f"{direction!r} — skipped"
            )
            return
        amount = abs(float(mv.get("amount") or 0.0))
        if amount == 0.0:
            return
        signed_amount = amount if direction == "IN" else -amount
        ref_prefix = f"BlueCash/{device_serial}/"
        ref_exact = f"{ref_prefix}{occurred_at.isoformat()}"
        Stmt = self.env["account.bank.statement.line"].sudo()
        # Първо — exact match.
        if Stmt.search_count([("payment_ref", "=", ref_exact)]):
            return
        # ±2 s tolerance: търсим близки lines със същата сума/посока.
        low = occurred_at - timedelta(seconds=2)
        high = occurred_at + timedelta(seconds=2)
        nearby = Stmt.search([
            ("payment_ref", "like", ref_prefix + "%"),
            ("date", ">=", fields.Datetime.to_string(low)),
            ("date", "<=", fields.Datetime.to_string(high)),
            ("amount", "=", signed_amount),
        ], limit=1)
        if nearby:
            return  # dedupe — within tolerance
        if dry_run:
            warnings.append(
                f"dry-run: would post cash {direction} {amount:.2f} "
                f"@ {occurred_at.isoformat()}"
            )
            return
        # Намираме cash journal на session-а.
        cash_journal = session.config_id.payment_method_ids.filtered(
            lambda m: m.is_cash_count
        )[:1].journal_id
        if not cash_journal:
            warnings.append(
                f"Cash movement {direction} {amount:.2f}: no cash "
                f"journal on POS config; skipped"
            )
            return
        # Закачаме към open bank statement за тоя journal, или
        # създаваме нов.
        stmt = self.env["account.bank.statement"].sudo().search([
            ("journal_id", "=", cash_journal.id),
            ("state", "=", "open"),
        ], limit=1, order="date desc")
        if not stmt:
            stmt = self.env["account.bank.statement"].sudo().create({
                "journal_id": cash_journal.id,
                "name": f"BlueCash sync {device_serial} "
                        f"{occurred_at.date().isoformat()}",
            })
        Stmt.create({
            "statement_id": stmt.id,
            "journal_id": cash_journal.id,
            "date": fields.Datetime.to_string(occurred_at),
            "amount": signed_amount,
            "payment_ref": ref_exact,
            "company_id": session.company_id.id,
        })

    # ─── Session close ──────────────────────────────────────────────

    def _close_session(self, session, warnings):
        """Drive pos.session → state='closed'.

        Ползваме стандартния `action_pos_session_closing_control`;
        той може да открие unposted invoices etc. — warning тогава.
        """
        # `with_user(SUPERUSER_ID)` защото идваме от `auth='public'`
        # request context — session.action_*() очаква real user със
        # POS rights. Service-ът вече е извикан със .sudo() от
        # controller-а, така че env е superuser-ен.
        try:
            session.with_user(
                SUPERUSER_ID).action_pos_session_closing_control()
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                f"Session close hook raised "
                f"{exc.__class__.__name__}: {exc}"
            )
