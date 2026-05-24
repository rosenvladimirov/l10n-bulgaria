"""
l10n.bg.fiscal.plu.device.line — per-device sync state of a Fiscal PLU.

Tracks the relationship "this PLU is programmed on this fiscal device".
One PLU can be pushed to multiple devices (multi-printer shop); one
device holds many PLUs. State tracks freshness:
  * synced    — last push confirmed; matches local snapshot
  * stale     — local PLU data changed (name/price) after last push
  * missing   — verification didn't find the PLU on the device
  * error     — push failed; see error_msg

A periodic verification wizard re-reads the device's PLU table and
flips state accordingly.
"""

from odoo import _, api, fields, models


class L10nBgFiscalPluDeviceLine(models.Model):
    _name = "l10n.bg.fiscal.plu.device.line"
    _description = "Fiscal PLU — Device Sync Line"
    _order = "plu_id, device_id"
    _rec_name = "device_id"

    plu_id = fields.Many2one(
        "l10n.bg.fiscal.plu",
        required=True,
        ondelete="cascade",
        index=True,
    )
    device_id = fields.Many2one(
        "fiscal.printer.device",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="plu_id.company_id", store=True, readonly=True, index=True,
    )

    state = fields.Selection(
        [
            ("synced", "Synced"),
            ("stale", "Stale (local changed)"),
            ("missing", "Missing on device"),
            ("error", "Push error"),
        ],
        default="synced",
        required=True,
        index=True,
    )
    last_synced_at = fields.Datetime(
        string="Last pushed at", readonly=True, copy=False,
    )
    last_verified_at = fields.Datetime(
        string="Last verified at", readonly=True, copy=False,
        help="When this line was last cross-checked with the device "
        "(verification wizard).",
    )
    error_msg = fields.Char(
        string="Error", readonly=True, copy=False,
    )

    # Snapshot of what we last pushed — used to detect drift vs the
    # current PLU price/name without hitting the device.
    pushed_name = fields.Char(readonly=True, copy=False)
    pushed_price = fields.Float(readonly=True, copy=False)
    pushed_vat_group = fields.Char(readonly=True, copy=False, size=4)

    _sql_constraints = [
        (
            "uniq_plu_device",
            "UNIQUE(plu_id, device_id)",
            "A PLU sync line per device must be unique.",
        ),
    ]
