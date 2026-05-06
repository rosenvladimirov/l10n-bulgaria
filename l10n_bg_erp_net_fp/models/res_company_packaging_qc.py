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
        domain=[("type", "=", "scale")],
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

    # ─── Grafana embed (monitoring tab) ─────────────────────────
    # Optional. When set, the "ErpNet.FP Monitoring" menu under
    # Settings opens the configured Grafana dashboard inside an
    # iframe — no separate browser tab needed for ops.
    erpnet_fp_grafana_url = fields.Char(
        string="Grafana base URL",
        config_parameter="l10n_bg_erp_net_fp.grafana_url",
        help="Public URL of your Grafana instance, e.g. "
             "https://grafana.lan.mcpworks.net. Leave empty to hide "
             "the monitoring menu.",
    )
    erpnet_fp_grafana_dashboard_uid = fields.Char(
        string="Default dashboard UID",
        config_parameter="l10n_bg_erp_net_fp.grafana_dashboard_uid",
        default="erpnet-fp-overview",
        help="The UID of the Grafana dashboard to embed. The bundled "
             "dashboard ships as `erpnet-fp-overview`.",
    )
