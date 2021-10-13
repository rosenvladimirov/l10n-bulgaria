# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class City(models.Model):
    _inherit = 'res.city'

    region_id = fields.Many2one(
        comodel_name='intrastat.region', string='Intrastat Region', domain="[('country_id', '=', country_id), ('is_city', '=', True)]")
