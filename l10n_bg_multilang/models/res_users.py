# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo import SUPERUSER_ID


class User(models.Model):
    _inherit = 'res.users'

    name = fields.Char(related='partner_id.name', inherited=True, translate=True)

