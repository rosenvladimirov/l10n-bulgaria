# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _

class AccountGroup(models.Model):
    _inherit = "account.group"

    name = fields.Char(translate=True)
