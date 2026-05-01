"""
pos.session — open a fiscal session on the Datecs device when the POS
session opens.

The fiscal session is a SEPARATE record from `pos.session` (the
browser/UI shift). They are linked via `pos_session_id` but never
identified — see `models/fiscal_session.py` for the rationale.

In external-mode (`pos.config.l10n_bg_fp_datecs_external_mode = True`)
opening the POS session also kicks off a PLU sync to the device. The
device's `on_sync_fail` policy determines how a sync failure affects
the POS opening: block (raise UserError), warning (continue + log),
or silent.

Z-report on close — out of scope for this batch. Cmd 0x45 (reports)
isn't in the facade yet; wire-up lands when it does.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = "pos.session"

    # ---- related view of fiscal device + run-state -----------------

    l10n_bg_fp_datecs_device_id = fields.Many2one(
        "l10n.bg.fp.device",
        string="Datecs PM Device",
        related="config_id.l10n_bg_fp_datecs_device_id",
        store=True,
        readonly=True,
    )
    l10n_bg_fp_datecs_external_mode = fields.Boolean(
        related="config_id.l10n_bg_fp_datecs_external_mode",
        store=True,
        readonly=True,
    )
    # Surfaced for the POS frontend so DatecsPMPrinter can fetch() the
    # ErpNet.FP-compatible proxy directly without going through Odoo.
    l10n_bg_fp_datecs_proxy_url = fields.Char(
        related="l10n_bg_fp_datecs_device_id.proxy_url",
        store=True,
        readonly=True,
    )
    l10n_bg_fp_datecs_printer_id = fields.Char(
        related="l10n_bg_fp_datecs_device_id.printer_id",
        store=True,
        readonly=True,
    )
    l10n_bg_fp_datecs_last_x_report = fields.Datetime(
        string="Last X (this session)",
        readonly=True,
    )
    l10n_bg_fp_datecs_z_report_printed = fields.Boolean(
        string="Z report printed",
        default=False,
        readonly=True,
    )
    l10n_bg_fp_datecs_z_report_datetime = fields.Datetime(
        string="Z report datetime",
        readonly=True,
    )
    l10n_bg_fp_datecs_session_id = fields.Many2one(
        "l10n.bg.fp.session",
        string="Datecs Fiscal Session",
        compute="_compute_l10n_bg_fp_datecs_session_id",
        help="The fiscal session created when this POS session opened "
        "(separate object — see models/fiscal_session.py).",
    )

    def _compute_l10n_bg_fp_datecs_session_id(self):
        Session = self.env["l10n.bg.fp.session"]
        for sess in self:
            sess.l10n_bg_fp_datecs_session_id = Session.search(
                [("pos_session_id", "=", sess.id)], limit=1
            )

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        res += [
            "l10n_bg_fp_datecs_device_id",
            "l10n_bg_fp_datecs_proxy_url",
            "l10n_bg_fp_datecs_printer_id",
            "l10n_bg_fp_datecs_external_mode",
            "l10n_bg_fp_datecs_last_x_report",
            "l10n_bg_fp_datecs_z_report_printed",
            "l10n_bg_fp_datecs_z_report_datetime",
        ]
        return res

    # ---- opening hook ---------------------------------------------

    def _set_opening_control_data(self, cashbox_value, notes):
        """Inherit the canonical open-hook in Odoo 18 (cash control or
        not, every opening path runs through this).
        """
        res = super()._set_opening_control_data(cashbox_value, notes)
        for session in self:
            session._l10n_bg_fp_datecs_open_fiscal_session()
        return res

    def _l10n_bg_fp_datecs_open_fiscal_session(self):
        """Open a fiscal session record linked back to this POS session.

        PLU sync, logo upload and config push are now the proxy's
        responsibility (admin manages them out-of-band via direct HTTP
        calls or the proxy's own management UI). The Odoo addon just
        records the lifecycle handle.
        """
        self.ensure_one()
        device = self.config_id.l10n_bg_fp_datecs_device_id
        if not device:
            return
        external = self.config_id.l10n_bg_fp_datecs_external_mode

        # Health-check the proxy so we discover unreachability now,
        # not at first receipt. on_sync_fail policy decides what to do.
        try:
            device.action_check_status()
            if not device.last_status_ok and device.on_sync_fail == "block":
                from odoo.exceptions import UserError
                raise UserError(
                    _("Fiscal proxy at %(url)s is unreachable; cannot "
                      "open POS session per `block` policy.",
                      url=device.proxy_url)
                )
        except Exception:
            if device.on_sync_fail == "block":
                raise
            _logger.exception(
                "Proxy health-check failed for POS session %s; policy "
                "permitted continuation",
                self.name,
            )

        # Create the fiscal session record. We do NOT call
        # any device command here (no equivalent of "begin Z-cycle"
        # exists in cmd map — fiscal sessions on Datecs are implicit
        # between Z-reports). The record is the Odoo-side handle.
        self.env["l10n.bg.fp.session"].create(
            {
                "name": self.env["ir.sequence"].next_by_code(
                    "l10n_bg_fp_datecs.session_sequence"
                )
                or "/",
                "device_id": device.id,
                "source": "pos_external" if external else "pos_printer",
                "pos_session_id": self.id,
            }
        )

    # ---- POS-form UI actions --------------------------------------

    def _require_device(self):
        """Raise if no Datecs device is configured for this session."""
        self.ensure_one()
        if not self.l10n_bg_fp_datecs_device_id:
            raise UserError(
                _("No Datecs PM fiscal device configured for this POS.")
            )
        return self.l10n_bg_fp_datecs_device_id

    def action_l10n_bg_fp_datecs_check_printer(self):
        """Check printer status (cmd 0x4A) — wrapper for device action."""
        device = self._require_device()
        return device.action_check_status()

    def action_l10n_bg_fp_datecs_print_x_report(self):
        """Print X report on the linked device."""
        device = self._require_device()
        if self.state != "opened":
            raise UserError(
                _("X report requires an open POS session.")
            )
        result = device.action_print_x_report()
        self.l10n_bg_fp_datecs_last_x_report = fields.Datetime.now()
        return result

    def action_l10n_bg_fp_datecs_print_z_report(self):
        """Print Z report on the linked device + mark this POS session."""
        device = self._require_device()
        if self.l10n_bg_fp_datecs_z_report_printed:
            raise UserError(
                _("Z report has already been printed for this POS session.")
            )
        result = device.action_print_z_report()
        self.write(
            {
                "l10n_bg_fp_datecs_z_report_printed": True,
                "l10n_bg_fp_datecs_z_report_datetime": fields.Datetime.now(),
            }
        )
        # Close the matching fiscal session record
        fp_session = self.l10n_bg_fp_datecs_session_id
        if fp_session and fp_session.state == "open":
            fp_session.write(
                {
                    "state": "closed",
                    "closed_at": fields.Datetime.now(),
                }
            )
        return result

    def action_l10n_bg_fp_datecs_print_duplicate(self):
        """Print a duplicate of the last fiscal receipt."""
        device = self._require_device()
        return device.action_print_duplicate()

    def action_l10n_bg_fp_datecs_cash_in(self):
        """Open the cash-operation wizard pre-filled for cash in."""
        self.ensure_one()
        return {
            "name": _("Cash in (служебно въведено)"),
            "type": "ir.actions.act_window",
            "res_model": "l10n.bg.fp.datecs.cash.operation.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_session_id": self.id,
                "default_operation_type": "in",
            },
        }

    def action_l10n_bg_fp_datecs_cash_out(self):
        """Open the cash-operation wizard pre-filled for cash out."""
        self.ensure_one()
        return {
            "name": _("Cash out (служебно изведено)"),
            "type": "ir.actions.act_window",
            "res_model": "l10n.bg.fp.datecs.cash.operation.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_session_id": self.id,
                "default_operation_type": "out",
            },
        }
