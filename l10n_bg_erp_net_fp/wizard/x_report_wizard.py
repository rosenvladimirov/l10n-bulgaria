"""
Mid-shift X-report wizard.

Lets a cashier or manager run an X-report on a chosen fiscal device
without leaving the pos.session form, and inspect the device's
response inline (totals, register state, errors). Useful in
external-POS mode to spot-check that the device's totals match the
imported pos.order records before close.

The wizard is a thin transient model — it doesn't store anything
permanently; results are visible until it's closed.
"""

import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nBgFiscalXReportWizard(models.TransientModel):
    _name = "l10n.bg.fiscal.x_report.wizard"
    _description = "Mid-shift X-report wizard"

    pos_session_id = fields.Many2one(
        "pos.session",
        readonly=True,
    )
    device_id = fields.Many2one(
        "fiscal.printer.device",
        required=True,
        domain="[('id', 'in', allowed_device_ids)]",
    )
    allowed_device_ids = fields.Many2many(
        "fiscal.printer.device",
        compute="_compute_allowed_device_ids",
    )
    response_text = fields.Text(
        readonly=True,
        string="Device response",
    )
    z_running_total = fields.Char(
        readonly=True,
        string="Running total",
    )
    has_response = fields.Boolean(
        compute="_compute_has_response",
    )

    @api.depends("response_text")
    def _compute_has_response(self):
        for rec in self:
            rec.has_response = bool(rec.response_text)

    @api.depends("pos_session_id")
    def _compute_allowed_device_ids(self):
        for rec in self:
            if rec.pos_session_id:
                rec.allowed_device_ids = (
                    rec.pos_session_id.config_id.l10n_bg_all_fiscal_devices
                )
            else:
                rec.allowed_device_ids = self.env["fiscal.printer.device"]

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        if ctx.get("active_model") == "pos.session" and ctx.get("active_id"):
            sess = self.env["pos.session"].browse(ctx["active_id"])
            res["pos_session_id"] = sess.id
            primary = sess.config_id.l10n_bg_fiscal_printer_id
            if primary:
                res["device_id"] = primary.id
        return res

    def action_run(self):
        """Run the X-report and populate response_text."""
        self.ensure_one()
        if not self.device_id:
            raise UserError(_("Pick a fiscal device first."))
        try:
            result = self.device_id.print_x_report()
        except Exception as exc:  # noqa: BLE001
            self.write({
                "response_text": f"ERROR: {exc}",
                "z_running_total": "",
            })
            return self._reopen()

        if not result:
            self.write({
                "response_text": _("Empty response from device."),
                "z_running_total": "",
            })
            return self._reopen()

        # Pretty-print the response so the cashier can read it
        try:
            pretty = json.dumps(result, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            pretty = str(result)
        # Try to extract a running-total summary line
        running = ""
        if isinstance(result, dict):
            data = result.get("data") or result
            total = (
                data.get("total")
                or data.get("totalAmount")
                or data.get("sum")
            )
            if total is not None:
                running = f"Σ {total}"
        self.write({
            "response_text": pretty,
            "z_running_total": running,
        })
        if self.pos_session_id:
            self.pos_session_id.l10n_bg_last_x_report = fields.Datetime.now()
        return self._reopen()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("X-report"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
