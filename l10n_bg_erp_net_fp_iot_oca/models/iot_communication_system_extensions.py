"""
Extends OCA's `iot.communication.system` with ErpNet.FP server URL
fields. The system is OCA's flat analogue of EE's `iot.box`; it has
no concept of "connection_mode" because the Odoo backend talks to
the ErpNet.FP HTTP server directly (no bus.bus proxy needed).
"""

from odoo import fields, models


class IoTCommunicationSystem(models.Model):
    _inherit = "iot.communication.system"

    erp_net_fp_url = fields.Char(
        string="ErpNet.FP URL",
        help="Base URL of the ErpNet.FP server that fronts this set of "
             "devices, e.g. https://erpnet-fp.lan.mcpworks.net. Used by "
             "iot.device.read_weight() and the discovery-style helpers.",
    )
    erp_net_fp_ssl_verify = fields.Boolean(
        string="Verify SSL",
        default=True,
        help="If unchecked, ErpNet.FP HTTPS requests skip certificate "
             "verification — only useful for self-signed dev setups.",
    )
    fiscal_printer_device_id = fields.Many2one(
        "fiscal.printer.device",
        string="Source fiscal.printer.device",
        help="Auto-set when the system is created via the bridge "
             "button on a fiscal.printer.device. The device stays the "
             "source of truth for host / printer_id; this system "
             "mirrors them for the IoT-side UI only.",
    )
