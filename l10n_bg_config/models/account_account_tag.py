#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class AccountAccountTag(models.Model):
    _inherit = 'account.account.tag'

    description = fields.Text('Description', translate=True)
