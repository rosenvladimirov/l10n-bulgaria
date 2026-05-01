"""
pos.printer — register Datecs PM as a printer type.

Adds a `datecs_pm` option to `printer_type` analogous to the sibling
`l10n_bg_erp_net_fp`'s `erp_net_fp` option. The frontend uses this
selection to decide whether to instantiate the Datecs PM driver vs.
the default IoT/ePosPrint logic.
"""

from odoo import api, fields, models


class PosPrinter(models.Model):
    _inherit = "pos.printer"

    printer_type = fields.Selection(
        selection_add=[("datecs_pm", "BG Datecs PM (direct)")],
        ondelete={"datecs_pm": "set default"},
    )
    l10n_bg_fp_datecs_device_id = fields.Many2one(
        "l10n.bg.fp.device",
        string="Datecs PM Device",
        domain=[("active", "=", True)],
        help="Datecs PM device this printer node should target.",
    )
    l10n_bg_fp_datecs_connection_type = fields.Selection(
        related="l10n_bg_fp_datecs_device_id.connection_type",
        store=True,
        readonly=True,
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result += [
            "l10n_bg_fp_datecs_device_id",
            "l10n_bg_fp_datecs_connection_type",
        ]
        return result
