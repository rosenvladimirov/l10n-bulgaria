# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    name = fields.Char(translate=True)
