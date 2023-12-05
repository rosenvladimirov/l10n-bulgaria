# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import fields, models, _


class CountryState(models.Model):
    _inherit = 'res.country.state'

    name = fields.Char(translate=True)
