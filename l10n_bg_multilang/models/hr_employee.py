#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HrEmployeePrivate(models.Model):
    _inherit = 'hr.employee'

    name = fields.Char(translate=True)
