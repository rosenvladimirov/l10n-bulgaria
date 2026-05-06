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

    default_packaging_tolerance_percent = fields.Float(
        related="company_id.default_packaging_tolerance_percent",
        readonly=False,
    )
    default_packaging_scale_id = fields.Many2one(
        related="company_id.default_packaging_scale_id",
        readonly=False,
    )
    default_packaging_empty_weight = fields.Float(
        related="company_id.default_packaging_empty_weight",
        readonly=False,
    )
