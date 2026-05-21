# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Transient model: enqueue a `program_vat` command on a remote proxy.

Pull-model — the proxy picks the command up on its next heartbeat and
calls its own `/printers/{id}/vat-rates` endpoint locally. The
result lands on the command record and is shown in the Commands tab.
"""
from __future__ import annotations

from odoo import _, fields, models


class ErpNetFpProgramVatWizard(models.TransientModel):
    _name = "erpnet.fp.program.vat.wizard"
    _description = "Queue: Program VAT rates on a remote ErpNet.FP printer"

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

    def action_program(self):
        self.ensure_one()
        self.proxy_id._enqueue_command("program_vat", {
            "printer_id": self.printer_id,
            "rates": {
                "a": self.rate_a, "b": self.rate_b,
                "c": self.rate_c, "d": self.rate_d,
            },
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Queued"),
                "message": _(
                    "VAT program command queued for printer %(p)s; "
                    "will run on the proxy's next heartbeat. Watch the "
                    "Commands tab on the proxy form for the result.",
                    p=self.printer_id,
                ),
                "type": "success",
                "sticky": False,
            },
        }
