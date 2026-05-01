"""
pos.config — link a POS configuration to a Datecs PM fiscal device.

Two operating modes:

* `external_mode = False` (default) — fiscal device acts as receipt
  printer behind Odoo POS. Sales originate in the POS UI; the printer
  receives `0x30` open / `0x31` sale / `0x35` total / `0x38` close
  per receipt. PLU sync to the device is NOT required.

* `external_mode = True` — "касов апарат като POS". Sales are entered
  on the device itself; Odoo only sets up the device (PLU sync, logo,
  stamp, header/footer, VAT) and reconciles X/Z reports. The POS UI
  session is used as a "shift" container around device-side sales.

Mapping is 1:1 (single device per POS config). Failover / redundancy is
out of scope for v18.0.1.0.0 — see ARCHITECTURE.md risk #5.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_bg_fp_datecs_device_id = fields.Many2one(
        "l10n.bg.fp.device",
        string="Datecs PM Fiscal Device",
        domain="[('company_id', '=', company_id)]",
        help="Direct-Python Datecs PM driver. Leave empty if this POS "
        "does not need a Datecs PM fiscal printer (it may use "
        "ErpNet.FP via l10n_bg_erp_net_fp instead).",
    )
    l10n_bg_fp_datecs_external_mode = fields.Boolean(
        string="Касов апарат като POS",
        help="Когато е включено, продажбите се правят на касовия апарат, "
        "не през Odoo POS UI. Odoo само sync-ва продуктите (PLU), "
        "лого/stamp, header/footer и параметрите на устройството, и "
        "обработва X/Z отчетите. Когато е изключено, касовият апарат "
        "работи само като receipt printer зад Odoo POS.",
    )
    l10n_bg_fp_datecs_auto_z_on_close = fields.Boolean(
        string="Auto Z on POS close",
        default=True,
        help="Print a Z-report on the device when the POS session closes "
        "(in addition to the device's own scheduled auto-Z, if any).",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        res += [
            "l10n_bg_fp_datecs_device_id",
            "l10n_bg_fp_datecs_external_mode",
            "l10n_bg_fp_datecs_auto_z_on_close",
        ]
        return res

    @api.constrains(
        "l10n_bg_fp_datecs_device_id", "l10n_bg_fp_datecs_external_mode"
    )
    def _check_l10n_bg_fp_datecs(self):
        for cfg in self:
            if (
                cfg.l10n_bg_fp_datecs_external_mode
                and not cfg.l10n_bg_fp_datecs_device_id
            ):
                raise UserError(
                    _(
                        "External-POS mode requires a Datecs PM fiscal "
                        "device on '%(name)s'.",
                        name=cfg.name,
                    )
                )
