# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class CountryState(models.Model):
    _inherit = 'res.country.state'

    name = fields.Char(translate=True)
