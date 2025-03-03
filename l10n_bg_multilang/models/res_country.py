# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CountryState(models.Model):
    _inherit = ["res.country.state", "res.transliterate.mixin"]
    _name = "res.country.state"

    name = fields.Char(translate=True)
