from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_bg_fiscal_printer_id = fields.Many2one(
        related='pos_config_id.l10n_bg_fiscal_printer_id',
        readonly=False,
        string='Fiscal printer'
    )

    l10n_bg_auto_z_on_close = fields.Boolean(
        related='pos_config_id.l10n_bg_auto_z_on_close',
        readonly=False,
        string='Automatic Z report'
    )

    # ─── Grafana embed (monitoring tab) ─────────────────────────
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
