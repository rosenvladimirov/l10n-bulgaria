"""
pos.order — proxy-aware extensions.

ADD-only — overrides `_add_mail_attachment` to allow sending the
receipt e-mail with no image attachment (the fiscal device already
produced the physical paper receipt; the e-mail is just a text
notification with order details + a link to the back-end record).

Adds four `l10n_bg_*` read-only fields populated by the
`l10n.bg.erp.net.fp.shift.sync` service when importing closed-shift
payloads from a BlueCash device (anchor_bluecash_shift_sync_contract).
"""

from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    # ─── Fields set by the shift_close importer ──────────────────────

    l10n_bg_uns = fields.Char(
        string="UNS",
        readonly=True, copy=False, index=True,
        help="Unique Sale Number on the fiscal device. Format: "
        "<serial>-<oper4>-<counter7>. Set when this order was created "
        "from a BlueCash shift-close payload. Used as the idempotency "
        "key — re-importing the same shift does not duplicate rows.",
    )
    l10n_bg_z_report_number = fields.Char(
        string="Z-report #",
        readonly=True, copy=False,
        help="Z-report serial number on the fiscal device when this "
        "order was registered.",
    )
    l10n_bg_device_serial = fields.Char(
        string="Fiscal device serial",
        readonly=True, copy=False, index=True,
        help="Serial number of the fiscal device that printed the "
        "physical receipt.",
    )
    l10n_bg_fiscal_day_number = fields.Integer(
        string="Fiscal day #",
        readonly=True, copy=False,
        help="Fiscal day counter on the device when this order was "
        "registered.",
    )

    def _add_mail_attachment(self, name, ticket, basic_ticket):
        # Empty ticket → no image — frontend pattern when the order has
        # already been printed by an external fiscal device, so we just
        # send the text-only e-mail. Core would crash on
        # `attachment.create(datas="")` so we short-circuit instead.
        if not ticket and not basic_ticket:
            return [(6, 0, [])]
        return super()._add_mail_attachment(name, ticket, basic_ticket)
