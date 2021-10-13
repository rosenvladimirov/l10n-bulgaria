# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class Employee(models.Model):
    _inherit = "hr.employee"

    name_related = fields.Char(related='resource_id.name', string="Resource Name", readonly=True, store=True, translate=True)
