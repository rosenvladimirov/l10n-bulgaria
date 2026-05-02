"""
pos.config — proxy-aware extensions.

ADD-only — does NOT change existing l10n_bg_fiscal_printer_id behaviour.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_bg_external_pos_mode = fields.Boolean(
        string="Cash register as POS (external)",
        help="When enabled, sales are entered on the fiscal device "
        "itself — Odoo POS UI is used as a 'shift' container around "
        "device-side sales. Sync (PLU + logo + stamp + parameters) is "
        "pushed to the device on POS open. When disabled (default), "
        "the device acts purely as a receipt printer behind Odoo POS.",
    )
    l10n_bg_auto_z_on_close = fields.Boolean(
        string="Auto Z on POS close",
        default=True,
        help="Print a Z-report on the device when the POS session "
        "closes (in addition to the device's own scheduled auto-Z).",
    )

    @api.constrains(
        "l10n_bg_fiscal_printer_id",
        "l10n_bg_external_pos_mode",
    )
    def _check_external_pos_needs_device(self):
        for cfg in self:
            if cfg.l10n_bg_external_pos_mode and not cfg.l10n_bg_fiscal_printer_id:
                raise UserError(
                    _("External-POS mode on '%(name)s' requires a "
                      "fiscal printer device assigned first.") % {
                        "name": cfg.name,
                    }
                )

    @api.model
    def _load_pos_data_fields(self, config_id):
        # IMPORTANT: pos.config core mixin default returns [] but
        # point_of_sale/models/pos_config.py:273 reads
        # `data[0]['use_pricelist']` unconditionally, so any non-empty
        # override MUST include use_pricelist (and the related fields
        # the JS frontend reads). Without these the POS fails to load
        # with `KeyError: 'use_pricelist'`.
        res = super()._load_pos_data_fields(config_id)
        for f in (
            "id",
            "name",
            "use_pricelist",
            "pricelist_id",
            "available_pricelist_ids",
            "currency_id",
            "company_id",
            "l10n_bg_external_pos_mode",
            "l10n_bg_auto_z_on_close",
        ):
            if f not in res:
                res.append(f)
        return res
