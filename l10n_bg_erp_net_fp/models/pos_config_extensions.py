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

    # Multi-device support — primary M2o stays for backward compat;
    # additional devices live on this M2m. The orchestrators iterate
    # `_l10n_bg_all_fiscal_devices` (computed union).
    l10n_bg_extra_fiscal_printer_ids = fields.Many2many(
        "fiscal.printer.device",
        "pos_config_extra_fiscal_printer_rel",
        "pos_config_id",
        "device_id",
        string="Additional fiscal printers",
        help="Extra fiscal devices (besides the primary). Used when a "
        "single POS configuration drives multiple cash registers in "
        "the same shop. Each device gets its own fiscal.session and "
        "Z-report cycle.",
    )
    l10n_bg_all_fiscal_devices = fields.Many2many(
        "fiscal.printer.device",
        compute="_compute_l10n_bg_all_fiscal_devices",
        string="All fiscal devices",
        help="Union of primary + extra fiscal printers — iterated by "
        "the open/close orchestrators.",
    )

    @api.depends(
        "l10n_bg_fiscal_printer_id",
        "l10n_bg_extra_fiscal_printer_ids",
    )
    def _compute_l10n_bg_all_fiscal_devices(self):
        for cfg in self:
            cfg.l10n_bg_all_fiscal_devices = (
                cfg.l10n_bg_fiscal_printer_id
                | cfg.l10n_bg_extra_fiscal_printer_ids
            )

    @api.constrains(
        "l10n_bg_fiscal_printer_id",
        "l10n_bg_extra_fiscal_printer_ids",
        "l10n_bg_external_pos_mode",
    )
    def _check_external_pos_needs_device(self):
        for cfg in self:
            if not cfg.l10n_bg_external_pos_mode:
                continue
            if not cfg.l10n_bg_all_fiscal_devices:
                raise UserError(
                    _("External-POS mode on '%(name)s' requires at "
                      "least one fiscal printer device assigned "
                      "(primary or in 'Additional fiscal printers').")
                    % {"name": cfg.name}
                )

    # NOTE: do NOT override `_load_pos_data_fields` on pos.config.
    # See `feedback_pos_config_load_pos_data_fields.md` — Odoo 18
    # core has many models reading `data['pos.config']['data'][0][X]`
    # in their _load_pos_data_domain (use_pricelist, printer_ids,
    # picking_type_id, fiscal_position_ids, group_pos_manager_id,
    # note_ids, etc.). Returning a non-empty list that misses any of
    # them breaks POS load with KeyError. The two l10n_bg_* flags
    # added on this model are server-side toggles only — they don't
    # need to live in the POS browser; backend cron / button handlers
    # read them via the standard ORM.
