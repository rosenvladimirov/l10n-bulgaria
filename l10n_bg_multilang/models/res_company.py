# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    lang = fields.Selection(
        related='partner_id.lang',
        string='Language',
        store=False,
        help="If the selected language is loaded in the system, all documents related to this contact will be printed in this language. If not, it will be English.")
    #name = fields.Char(translate=True)
    street = fields.Char(translate=True)
    street2 = fields.Char(translate=True)
    city = fields.Char(translate=True)
    report_header = fields.Text(translate=True)
