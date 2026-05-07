"""
res.company defaults for packaging weight QC.

Per-company configuration that flows down to MOs and pickings as the
default tolerance and scale device when no record-level override is
set.
"""

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    default_packaging_tolerance_percent = fields.Float(
        string="Default packaging weight tolerance (%)",
        default=5.0,
        help="Default ± tolerance percentage for MO and picking "
             "weight verification. BoMs and individual records can "
             "override this.",
    )
    default_packaging_scale_id = fields.Many2one(
        "iot.device",
        string="Default packaging scale",
        domain=[("erp_net_fp_kind", "=", "scale")],
        help="Default scale used when an MO or picking doesn't "
             "specify one explicitly.",
    )
    default_packaging_empty_weight = fields.Float(
        string="Default empty package weight (kg)",
        digits=(12, 3),
        default=0.0,
        help="Default weight of the empty packaging used in pickings "
             "(box, crate, etc.). BoMs override this for MOs.",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Field names MUST NOT start with `default_` — Odoo's res.config
    # interprets `default_<name>` as a value to write to ir.default and
    # demands a `default_model` attribute. We keep the underlying
    # company fields named `default_packaging_*` for clarity (they are
    # company-wide defaults), and just expose them on the settings
    # screen under shorter names.
    packaging_tolerance_percent = fields.Float(
        related="company_id.default_packaging_tolerance_percent",
        readonly=False,
    )
    packaging_scale_id = fields.Many2one(
        related="company_id.default_packaging_scale_id",
        readonly=False,
    )
    packaging_empty_weight = fields.Float(
        related="company_id.default_packaging_empty_weight",
        readonly=False,
    )

    # Grafana fields stay in core l10n_bg_erp_net_fp/models/res_config_settings.py
    # — they are independent of iot/packaging QC.
