# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    uid = fields.Char(related='partner_id.uid', string="UIC")
    uid_type = fields.Selection(related="partner_id.uid_type", string='Type of UID', help="Choice type of UID.")
    fax = fields.Char(related='partner_id.fax', string='Fax')
    mobile = fields.Char(related='partner_id.mobile', string='Mobile Phone')
