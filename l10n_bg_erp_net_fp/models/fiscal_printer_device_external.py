"""
fiscal.printer.device — Phase 2 external POS mode push helpers.

These methods feed the device with the configuration it needs to act
as the primary POS in external mode: VAT groups, operators, the PLU
table from `l10n.bg.fiscal.plu` registry. They reuse the existing
`_proxy_post` HTTP helper (frame-logged, error-routed).

NOTE: the legacy `action_sync_plu()` (which reads plu_number from
`product.product` directly) stays for backward compat with shops
that haven't migrated to the registry yet. New module v18.0.10.3.0+
recommends `_l10n_bg_push_plu_registry()` instead.
"""

import base64
import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


# Truncate names to fit on a fiscal receipt line (most БГ devices
# accept up to 34 chars on the article line; safe lower bound).
PLU_NAME_MAX = 34

# Bulk push batch size — keeps the proxy round-trip under ~5s for
# typical БГ retail (1500-2000 active PLUs).
PLU_BATCH_SIZE = 200


class FiscalPrinterDevice(models.Model):
    _inherit = "fiscal.printer.device"

    # ------------------------------------------------------------------
    # PLU push from registry
    # ------------------------------------------------------------------

    def _l10n_bg_push_plu_registry(self, plu_records):
        """Push a set of `l10n.bg.fiscal.plu` records to this device.

        Sends in batches (PLU_BATCH_SIZE per call) via the proxy's
        bulk endpoint (`printers/{id}/plu/sync`). Updates each PLU's
        push_state + last_pushed_at on success.

        Returns: True on full success, False on any batch failure.
        """
        self.ensure_one()
        if not plu_records:
            return True

        # Capacity guard — refuse to push more than the device can hold.
        # `plu_capacity` is populated from device info on connect; 0 means
        # unknown so we skip the check (don't block on missing metadata).
        if self.plu_capacity and len(plu_records) > self.plu_capacity:
            from odoo.exceptions import UserError
            raise UserError(_(
                "PLU push aborted: %(want)s active PLUs > device "
                "capacity %(cap)s. Run the 'Top-N best-sellers' wizard "
                "to archive low-velocity slots first."
            ) % {"want": len(plu_records), "cap": self.plu_capacity})

        all_ok = True
        pushed_ids = []
        failed_ids = []
        for batch in self._batched(plu_records, PLU_BATCH_SIZE):
            payload_items = [self._plu_record_to_payload(p) for p in batch]
            result = self._proxy_post(
                "plu/sync",
                {"items": payload_items},
                log_endpoint="printers/.../plu/sync",
            )
            if result is None:
                # _proxy_post already logged and applied sync failure
                all_ok = False
                failed_ids.extend(batch.ids)
                batch.write({
                    "push_state": "error",
                    "push_message": "Push to device failed (see frame log).",
                })
            else:
                pushed_ids.extend(batch.ids)
                batch.write({
                    "push_state": "pushed",
                    "push_message": "Pushed successfully.",
                    "last_pushed_at": fields.Datetime.now(),
                })

        self.write({
            "last_plu_sync": fields.Datetime.now(),
            "plu_programmed": len(pushed_ids),
        })
        return all_ok

    def _plu_record_to_payload(self, plu):
        """Convert an `l10n.bg.fiscal.plu` record into the proxy
        `plu/sync` payload item shape.
        """
        # First product's barcode acts as canonical for scan-routing.
        canonical = plu.product_ids[:1]
        return {
            "plu": plu.plu_number,
            "name": (plu.name or "")[:PLU_NAME_MAX],
            "price": plu.price,
            "vat_group": self._vat_group_to_device_letter(plu.vat_group_id),
            "department": plu.department_id or 1,
            "barcode": (canonical.barcode if canonical else "") or "",
            "currency": plu.currency_id.name or "BGN",
        }

    @staticmethod
    def _vat_group_to_device_letter(vat_group):
        """Map account.tax.group → БГ device VAT letter (А/Б/В/Г).
        Falls back to 'Б' (standard 20% VAT) when no mapping found.
        """
        if not vat_group:
            return "Б"
        return vat_group.l10n_bg_fiscal_tax_group or "Б"

    @staticmethod
    def _batched(records, n):
        """Yield consecutive batches of size `n` from a recordset."""
        ids = list(records.ids)
        for i in range(0, len(ids), n):
            yield records.browse(ids[i:i + n])

    # ------------------------------------------------------------------
    # VAT groups push
    # ------------------------------------------------------------------

    def _l10n_bg_push_vat_groups(self):
        """Push the VAT-group → device-letter mapping to the device.
        Reads all configured `account.tax.group` for this company that
        have a БГ letter assigned.
        """
        self.ensure_one()
        Group = self.env["account.tax.group"]
        groups = Group.search([("l10n_bg_fiscal_tax_group", "!=", False)])
        if not groups:
            return True
        payload = {
            "groups": [
                {
                    "letter": g.l10n_bg_fiscal_tax_group,
                    "name": g.name,
                    # Each group typically owns one tax with the rate
                    "rate": (g.tax_ids[:1].amount or 0.0),
                }
                for g in groups
            ]
        }
        result = self._proxy_post(
            "vat-rates", payload,
            log_endpoint="printers/.../vat-rates",
        )
        return result is not None

    # ------------------------------------------------------------------
    # Operators push
    # ------------------------------------------------------------------

    def _l10n_bg_push_operators(self, pos_config):
        """Push cashier operator codes/passwords to the device.
        Sources users from pos.config.basic_employee_ids (if any) or
        all users with a `l10n_bg_fp_operator` set.
        """
        self.ensure_one()
        users = self._l10n_bg_collect_operators(pos_config)
        if not users:
            return True
        payload = {
            "operators": [
                {
                    "id": u.id,
                    "code": (u.l10n_bg_fp_operator or "")[:8],
                    "name": u.name[:24],
                    "password": (u.l10n_bg_fp_operator_password or "")[:8],
                }
                for u in users
                if u.l10n_bg_fp_operator
            ]
        }
        if not payload["operators"]:
            return True
        result = self._proxy_post(
            "operators", payload,
            log_endpoint="printers/.../operators",
        )
        return result is not None

    def _l10n_bg_collect_operators(self, pos_config):
        """Return res.users recordset to push as operators.
        Prefers explicit POS-config cashiers; falls back to all users
        in the manager group with a fiscal operator code set.
        """
        users = self.env["res.users"]
        # Try pos.config.basic_employee_ids — Odoo 18 standard
        if "basic_employee_ids" in pos_config._fields:
            employees = pos_config.basic_employee_ids
            user_ids = employees.mapped("user_id").ids
            if user_ids:
                users = self.env["res.users"].browse(user_ids)
        if not users:
            # Fallback — anyone with operator code configured
            users = self.env["res.users"].search([
                ("l10n_bg_fp_operator", "!=", False),
            ])
        return users

    # ------------------------------------------------------------------
    # Phase 3 — close-time pull + Z + parsing
    # ------------------------------------------------------------------

    def _l10n_bg_pull_sales(self, from_dt, to_dt=None):
        """Pull fiscal receipts from the device journal between two
        timestamps. Returns a normalised list of receipt dicts:

            [
              {
                "number": int,                  # fiscal receipt number
                "datetime": str (ISO),
                "operator": str,
                "items": [
                    {"plu": int, "name": str, "qty": float,
                     "price": float, "vat": str}, ...],
                "payments": [
                    {"kind": "cash"|"card"|"voucher"|"other",
                     "amount": float}, ...],
                "total": float,
              }, ...
            ]

        Returns an empty list on transport failure (failures already
        logged via _proxy_post / _make_request).
        """
        self.ensure_one()
        from_iso = from_dt.isoformat() if from_dt else None
        to_iso = (to_dt or fields.Datetime.now()).isoformat()
        try:
            raw = self.get_journal_info(from_date=from_iso, to_date=to_iso)
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "Failed to pull sales from device %s: %s", self.name, exc
            )
            return []
        if not raw:
            return []
        return self._normalise_journal_payload(raw)

    @staticmethod
    def _normalise_journal_payload(raw):
        """Convert the device's journal JSON into a stable shape.

        ErpNet.FP's `/printers/{id}/journal` response varies across
        device families (Datecs ISL/PM, Tremol, Daisy). We accept
        common shapes and degrade gracefully on missing fields.
        """
        receipts_in = (
            raw.get("receipts")
            or raw.get("documents")
            or raw.get("items")
            or []
        )
        out = []
        for r in receipts_in:
            items = []
            for it in r.get("items") or r.get("lines") or []:
                items.append({
                    "plu": int(it.get("plu") or it.get("pluNumber") or 0),
                    "name": it.get("name") or it.get("article") or "",
                    "qty": float(it.get("qty") or it.get("quantity") or 1.0),
                    "price": float(it.get("price") or it.get("unitPrice") or 0.0),
                    "vat": (it.get("vat") or it.get("vatGroup") or "Б"),
                })
            payments = []
            for pay in r.get("payments") or []:
                k = (pay.get("type") or pay.get("kind") or "").lower()
                if k in ("cash", "пари", "брой"):
                    kind = "cash"
                elif k in ("card", "карта", "credit", "debit"):
                    kind = "card"
                elif k in ("voucher", "coupon", "ваучер", "купон"):
                    kind = "voucher"
                else:
                    kind = "other"
                payments.append({
                    "kind": kind,
                    "amount": float(pay.get("amount") or 0.0),
                })
            out.append({
                "number": int(
                    r.get("number") or r.get("receiptNumber")
                    or r.get("docNumber") or 0
                ),
                "datetime": (
                    r.get("datetime") or r.get("dateTime") or r.get("date")
                ),
                "operator": str(r.get("operator") or ""),
                "items": items,
                "payments": payments,
                "total": float(r.get("total") or r.get("amount") or 0.0),
            })
        return out

    # Transient device-side errors that warrant retrying the Z command.
    # Permanent errors (auth, invalid command) are NOT retried.
    Z_RETRY_HINTS = (
        "timeout", "timed out", "connection",
        "paper", "хартия",
        "busy", "occupied", "заето",
        "transient", "temporarily",
    )

    def _l10n_bg_print_z(self, max_attempts=3, retry_delay=2.0):
        """Trigger Z-report on the device with bounded retry.

        Returns dict: {"z_number": int, "total": float, "ok": bool,
                       "message": str, "attempts": int}.

        Retry logic:
          - Up to `max_attempts` total tries (default 3)
          - Wait `retry_delay` seconds between retries
          - Only retry on transient hints (paper-out, timeout, busy)
          - Permanent errors fail-fast on first attempt

        After final failure the caller (cron / close orchestrator)
        keeps the fiscal session in `open` / `closed_partial` and
        posts a mail.activity alert to the responsible manager.
        """
        self.ensure_one()
        import time

        last_msg = ""
        for attempt in range(1, max_attempts + 1):
            try:
                result = self.print_z_report()
            except Exception as exc:  # noqa: BLE001
                last_msg = str(exc)[:200]
                _logger.warning(
                    "Z-report attempt %d/%d failed on %s: %s",
                    attempt, max_attempts, self.name, last_msg,
                )
                if not self._is_transient_error(last_msg):
                    return {
                        "z_number": 0, "total": 0.0, "ok": False,
                        "message": last_msg, "attempts": attempt,
                    }
                if attempt < max_attempts:
                    time.sleep(retry_delay)
                continue
            if not result:
                last_msg = "Empty Z response"
                if attempt < max_attempts:
                    time.sleep(retry_delay)
                continue
            # Successful response — parse and return
            data = result.get("data") if isinstance(result, dict) else {}
            if not data and isinstance(result, dict):
                data = result
            return {
                "z_number": int(
                    data.get("zNumber") or data.get("zReportNumber")
                    or data.get("number") or 0
                ),
                "total": float(
                    data.get("total") or data.get("totalAmount") or 0.0
                ),
                "ok": True,
                "message": "Z-report printed (attempt %d/%d)." % (
                    attempt, max_attempts,
                ),
                "attempts": attempt,
            }

        return {
            "z_number": 0, "total": 0.0, "ok": False,
            "message": last_msg or "Z-report failed after retries.",
            "attempts": max_attempts,
        }

    @classmethod
    def _is_transient_error(cls, msg):
        """Heuristic: does this error message look retryable?"""
        m = (msg or "").lower()
        return any(h in m for h in cls.Z_RETRY_HINTS)
