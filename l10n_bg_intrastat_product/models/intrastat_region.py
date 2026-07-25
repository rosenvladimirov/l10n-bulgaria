#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class IntrastatRegion(models.Model):
    _inherit = "intrastat.region"

    description = fields.Char(translate=True)
