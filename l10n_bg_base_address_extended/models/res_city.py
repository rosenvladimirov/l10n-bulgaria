# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class City(models.Model):
    _inherit = 'res.city'

    street_ids = fields.One2many('res.city.street', "city_id", string='Street')


class StreetCity(models.Model):
    _name = 'res.city.street'
    _desctription = 'Street address in cites'
    _order = 'name, number, number2'

    name = fields.Char("Street name", index=True, translate=True)
    number = fields.Char("House Number", translate=True)
    number2 = fields.Char("Door Number", translate=True)
    building_number = fields.Char('Bulding Number', translate=True)
    floor_number = fields.Char('Floor Number', translate=True)
    sector_number = fields.Char('Sector Number', translate=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    city_id = fields.Many2one('res.city', string='City', required=True)

    @api.model_cr
    def init(self):
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('res_city_street_nnn_index',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX res_city_street_nnn_index ON res_city_street (name, number, number2)')
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('res_city_street_full_index',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX res_city_street_full_index ON res_city_street (sector_number, name, number, building_number, floor_number, number2)')

