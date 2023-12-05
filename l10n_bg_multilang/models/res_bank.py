# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class Bank(models.Model):
    _inherit = 'res.bank'

    name = fields.Char(translate=True)