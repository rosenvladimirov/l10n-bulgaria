"""
Packaging-weight QC — abstract mixin reused by mrp.production and
stock.picking.

Public flow:
    rec.action_verify_packaging_weight()
        ↓
    1. Resolve a scale device:
         - explicit `packaging_scale_device_id` on the record, OR
         - company default (`res.company.default_packaging_scale_id`)
    2. Read weight via `iot.device.read_weight()` (already wired through
       Phase 2 — direct or browser-proxy mode, transparent to caller).
    3. Compute expected weight from `_packaging_expected_weight()` —
       subclass-specific (BoM × qty for MO, move lines for picking).
    4. Compare actual vs expected ± tolerance.
    5. Write fields:
         packaging_actual_weight       = float, kg, last reading
         packaging_expected_weight     = float, kg, last computed
         packaging_weight_state        = pending / pass / fail
         packaging_weight_verified_at  = datetime
         packaging_weight_message      = human summary
    6. Return ir.actions.client notification (pass/fail toast).

Tolerance resolution order (subclass overrides one of the first two):
    1. record-level override (e.g. mrp.production.weight_tolerance_percent)
    2. parent-level default (e.g. mrp.bom.weight_tolerance_percent)
    3. company default (`res.company.default_packaging_tolerance_percent`)
    4. fallback: 5.0 %
"""

import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_TOLERANCE_PERCENT = 5.0


class PackagingWeighableMixin(models.AbstractModel):
    _name = "l10n.bg.packaging.weighable.mixin"
    _description = "Packaging weight QC — abstract mixin"

    # ─── State / measurement fields ─────────────────────────────

    packaging_scale_device_id = fields.Many2one(
        "iot.device",
        string="Scale device",
        domain=[("erp_net_fp_kind", "=", "scale")],
        help="Scale to use for packaging weight verification. Falls "
             "back to company default if not set.",
    )

    packaging_actual_weight = fields.Float(
        string="Actual weight (kg)",
        digits=(12, 3),
        readonly=True,
        copy=False,
    )

    packaging_expected_weight = fields.Float(
        string="Expected weight (kg)",
        digits=(12, 3),
        readonly=True,
        copy=False,
    )

    packaging_weight_state = fields.Selection(
        [
            ("pending", "Not verified"),
            ("pass", "Verified — within tolerance"),
            ("fail", "Verified — out of tolerance"),
        ],
        string="Weight QC",
        default="pending",
        readonly=True,
        copy=False,
        tracking=True,
    )

    packaging_weight_verified_at = fields.Datetime(
        string="Verified at",
        readonly=True,
        copy=False,
    )

    packaging_weight_message = fields.Char(
        string="Verification message",
        readonly=True,
        copy=False,
    )

    # ─── Subclass-supplied hooks ────────────────────────────────

    def _packaging_expected_weight(self):
        """Return expected total weight (kg) excluding empty packaging.
        Subclass implements: MO sums BoM lines, picking sums move
        lines, etc."""
        self.ensure_one()
        raise NotImplementedError(
            "%s must implement _packaging_expected_weight()" % self._name
        )

    def _packaging_empty_weight(self):
        """Return weight of the empty container/box (kg). Default 0."""
        self.ensure_one()
        return 0.0

    def _packaging_tolerance_percent(self):
        """Return tolerance % for this record."""
        self.ensure_one()
        company = (
            self.company_id
            if "company_id" in self._fields and self.company_id
            else self.env.company
        )
        return getattr(
            company, "default_packaging_tolerance_percent", None
        ) or DEFAULT_TOLERANCE_PERCENT

    # ─── Public API ─────────────────────────────────────────────

    def action_verify_packaging_weight(self):
        """Read the configured scale, compare to expected ± tolerance,
        update state fields, return a user-facing notification."""
        self.ensure_one()
        device = self._resolve_scale_device()
        if not device:
            raise UserError(_(
                "No scale device configured. Set "
                "`packaging_scale_device_id` on this record or a "
                "default on the company."
            ))

        try:
            actual = device.read_weight()
        except Exception as exc:
            _logger.exception("Scale read failed for %s", self.display_name)
            raise UserError(_(
                "Could not read scale %(scale)s: %(err)s"
            ) % {"scale": device.name, "err": exc})

        if actual is None:
            raise UserError(_(
                "Scale %s returned no value (unstable / unreachable)."
            ) % device.name)

        expected = self._packaging_expected_weight()
        empty = self._packaging_empty_weight()
        target = expected + empty
        tol_pct = self._packaging_tolerance_percent()
        tol_kg = abs(target) * (tol_pct / 100.0)
        delta = actual - target
        in_tolerance = abs(delta) <= tol_kg

        self.write({
            "packaging_actual_weight": actual,
            "packaging_expected_weight": target,
            "packaging_weight_state": "pass" if in_tolerance else "fail",
            "packaging_weight_verified_at": fields.Datetime.now(),
            "packaging_weight_message": _build_message(
                actual, target, tol_pct, tol_kg, delta, in_tolerance
            ),
        })

        notif_type = "success" if in_tolerance else "danger"
        title = _("Weight OK") if in_tolerance else _("Weight FAIL")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": self.packaging_weight_message,
                "type": notif_type,
                "sticky": not in_tolerance,
            },
        }

    # ─── Internals ──────────────────────────────────────────────

    def _resolve_scale_device(self):
        self.ensure_one()
        if self.packaging_scale_device_id:
            return self.packaging_scale_device_id
        company = (
            self.company_id
            if "company_id" in self._fields and self.company_id
            else self.env.company
        )
        return getattr(company, "default_packaging_scale_id", None) or None


def _build_message(actual, target, tol_pct, tol_kg, delta, ok):
    """One-line human-readable summary for notifications + tracking."""
    sign = "+" if delta >= 0 else ""
    base = (
        f"actual {actual:.3f} kg vs expected {target:.3f} kg "
        f"(±{tol_pct:.1f}% = ±{tol_kg:.3f} kg) — Δ={sign}{delta:.3f} kg"
    )
    if ok:
        return f"OK · {base}"
    if delta < 0:
        return f"UNDER-WEIGHT · {base} · check for missing components"
    return f"OVER-WEIGHT · {base} · check for extra items"
