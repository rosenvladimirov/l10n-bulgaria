# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    name = fields.Char(translate=True)
