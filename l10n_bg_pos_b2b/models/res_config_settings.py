# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_l10n_bg_b2b_mode = fields.Selection(
        related="pos_config_id.l10n_bg_b2b_mode", readonly=False
    )
    pos_l10n_bg_b2b_default_doc_mode = fields.Selection(
        related="pos_config_id.l10n_bg_b2b_default_doc_mode", readonly=False
    )
    pos_l10n_bg_b2b_credit_policy = fields.Selection(
        related="pos_config_id.l10n_bg_b2b_credit_policy", readonly=False
    )
    pos_l10n_bg_b2b_offline_order_cap = fields.Monetary(
        related="pos_config_id.l10n_bg_b2b_offline_order_cap", readonly=False
    )
    pos_l10n_bg_b2b_guard_mode = fields.Selection(
        related="pos_config_id.l10n_bg_b2b_guard_mode", readonly=False
    )
