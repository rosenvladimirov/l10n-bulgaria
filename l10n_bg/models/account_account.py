# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError


class AccountAccount(models.Model):
    _inherit = "account.account"

    clear_balance = fields.Boolean()
