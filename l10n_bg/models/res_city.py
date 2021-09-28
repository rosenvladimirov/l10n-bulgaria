# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class CityTypes(models.Model):
    _name = "res.city.types"
    _description = "Types of cities"
    _order = "name"

    code = fields.Char("Code", translate=True)
    name = fields.Char("Name", index=True, translate=True)


class City(models.Model):
    _inherit = 'res.city'

    type_village_city_id = fields.Many2one("res.city.types", string="Type of settlement")
    ekatte = fields.Char("EKATTE")
    code = fields.Char(string='City Code', help='The state code.')
    city_hall_id = fields.Many2one('res.city', 'City Hall',
                                   domain="[('country_id', '=', country_id), ('structure_type', '=', 'cityhall')]")
    municipality_id = fields.Many2one('res.city', 'Municipality',
                                      domain="[('country_id', '=', country_id), ('structure_type', '=', 'municipality')]")
    has_taxoffice = fields.Boolean("Has Tax Office")
    structure_type = fields.Selection(string='Country Structure',
                                      selection=[('normal', 'settlement'), ('cityhall', 'City Hall'),
                                                 ('municipality', 'Municipality')], default='normal')
