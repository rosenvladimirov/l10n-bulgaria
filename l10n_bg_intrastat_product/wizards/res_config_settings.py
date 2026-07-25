#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    intrastat_origin_transport_id = fields.Many2one(
        related="company_id.intrastat_origin_transport_id",
        readonly=False,
        default=lambda self: self.env.ref("base.bg").id,
    )
