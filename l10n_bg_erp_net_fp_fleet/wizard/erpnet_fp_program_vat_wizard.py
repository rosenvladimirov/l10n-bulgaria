# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Transient model: program VAT rates on a remote fiscal printer.

Fiscal printers in Bulgaria reject sales lines whose VAT class isn't
programmed on the device — this commonly throws "Forbidden VAT" at
sale time, blocking the cashier. The proxy exposes
``GET /printers/{id}/vat-rates`` (read current programming) and
``POST /printers/{id}/vat-rates`` (program new values), gated by the
admin token. This wizard collects the four BG groups (А=20%, Б=20%,
В=9%, Г=0% by default) and proxies the call.
"""
from __future__ import annotations

import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ErpNetFpProgramVatWizard(models.TransientModel):
    _name = "erpnet.fp.program.vat.wizard"
    _description = "Program VAT rates on a remote ErpNet.FP printer"

    proxy_id = fields.Many2one(
        "erpnet.fp.proxy", required=True, ondelete="cascade",
        readonly=True,
    )
    printer_id = fields.Char(
        required=True, default="dp150",
        help="Printer ID as configured on the proxy (matches the "
             "`id:` key under `printers:` in config.yaml).",
    )
    rate_a = fields.Float(string="Group А", default=20.0, digits=(6, 2))
    rate_b = fields.Float(string="Group Б", default=20.0, digits=(6, 2))
    rate_c = fields.Float(string="Group В", default=9.0,  digits=(6, 2))
    rate_d = fields.Float(string="Group Г", default=0.0,  digits=(6, 2))
    current_rates_json = fields.Text(readonly=True)

    @api.onchange("proxy_id", "printer_id")
    def _onchange_load_current(self):
        for rec in self:
            if not (rec.proxy_id and rec.printer_id):
                rec.current_rates_json = ""
                continue
            try:
                result = rec.proxy_id._admin_call(
                    "GET",
                    f"/printers/{rec.printer_id}/vat-rates",
                    timeout=15,
                )
                rec.current_rates_json = json.dumps(result, indent=2,
                                                     sort_keys=True)
            except UserError as exc:
                rec.current_rates_json = f"(error: {exc})"

    def action_program(self):
        self.ensure_one()
        body = {
            "rates": {
                "a": self.rate_a,
                "b": self.rate_b,
                "c": self.rate_c,
                "d": self.rate_d,
            },
        }
        result = self.proxy_id._admin_call(
            "POST",
            f"/printers/{self.printer_id}/vat-rates",
            json_body=body,
            timeout=30,
        )
        self.proxy_id.message_post(body=_(
            "VAT rates programmed on printer %(p)s: А=%(a)s%%, Б=%(b)s%%, "
            "В=%(c)s%%, Г=%(d)s%%. Result: %(r)s",
            p=self.printer_id, a=self.rate_a, b=self.rate_b,
            c=self.rate_c, d=self.rate_d,
            r=json.dumps(result),
        ))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("VAT programmed"),
                "message": _("Printer %(p)s now reports rates A=%(a)s, B=%(b)s, "
                             "C=%(c)s, D=%(d)s",
                             p=self.printer_id, a=self.rate_a, b=self.rate_b,
                             c=self.rate_c, d=self.rate_d),
                "type": "success",
                "sticky": False,
            },
        }
