# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class City(models.Model):
    _inherit = 'res.city'

    def _domain_region_id(self):
        return [('country_id', '=', self.env.user.country_id.id)]

    region_id = fields.Many2one(
        comodel_name='intrastat.region',
        string='Intrastat Region',
        domain=lambda self: self._domain_region_id())
