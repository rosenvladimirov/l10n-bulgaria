# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

