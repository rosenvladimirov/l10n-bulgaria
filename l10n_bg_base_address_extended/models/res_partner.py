# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = ['res.partner']
    _name = 'res.partner'

    street_building_number = fields.Char('Bulding Number', compute='_split_street',
                                         inverse='_set_street', store=True, translate=True)
    street_floor_number = fields.Char('Floor Number', compute='_split_street',
                                      inverse='_set_street', store=True, translate=True)
    street_sector_number = fields.Char('Sector Name/Number', compute='_split_street',
                                       inverse='_set_street', store=True, trnslate=True)

    @api.multi
    def get_formated_street(self):
        for partner in self:
            street_format = (partner.country_id.street_format or
                             '%(street_number)s/%(street_number2)s %(street_name)s')
            args = {}
            for field in partner.get_street_fields():
                args[field] = getattr(self, field) or ''
        return street_format % args

    def get_street_fields(self):
        street_fields = super(Partner, self).get_street_fields()
        street_fields += ('street_building_number', 'street_floor_number', 'street_sector_number')
        return street_fields

    def write(self, vals):
        res = super(Partner, self).write(vals)
        if ('country_id' and 'city_id') in vals:
            country = self.env['res.country'].browse(
                vals.get('country_id', False) and vals['country_id'] or self.country_id.id)
            if country.enforce_cities:
                street = False
                res_street = {'name': self.street_name, 'country_id': self.country_id.id, 'city_id': self.city_id.id}
                if self.street_name and (self.street_number or self.street_number2) and not (
                    self.street_building_number or self.street_floor_number or self.street_sector_number):
                    # name, number, number2
                    street = self.env['res.city.street'].search([('name', 'ilike', self.street_name),
                                                                 ('number', 'ilike', self.street_number or ''),
                                                                 ('number2', 'ilike', self.street_number2 or '')],
                                                                limit=1)
                elif self.street_name and (
                    self.street_building_number or self.street_floor_number or self.street_sector_number):
                    # sector_number, name, number, building_number, floor_number, number2
                    street = self.env['res.city.street'].search([('sector_number', 'ilike', self.street_sector_number),
                                                                 ('name', 'ilike', self.street_name),
                                                                 ('number', 'ilike', self.street_number or ''),
                                                                 ('building_number', 'ilike',
                                                                  self.street_building_number or ''),
                                                                 ('floor_number', 'ilike',
                                                                  self.street_floor_number or ''),
                                                                 ('number2', 'ilike', self.street_number2 or '')
                                                                 ], limit=1)
                if self.street_number:
                    res_street.update({'number': self.street_number})
                elif self.street_number2:
                    res_street.update({'number2': self.street_number2})
                elif self.street_sector_number:
                    res_street.update({'sector_number': self.street_sector_number})
                elif self.street_building_number:
                    res_street.update({'building_number': self.street_building_number})
                elif self.street_building_number:
                    res_street.update({'floor_number': self.street_floor_number})

                if street:
                    street.write(res_street)
                else:
                    self.env['res.city.street'].create(res_street)
        return res
