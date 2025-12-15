# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools, _


class Lang(models.Model):
    _inherit = "res.lang"

    transliterate = fields.Boolean(string="Transliterate")
