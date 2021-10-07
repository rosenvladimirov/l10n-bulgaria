# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    territorial_tax_id = fields.Many2one('res.territorial.tax.directorates', 'Territorial tax department')
    tax_office_id = fields.Many2one('res.territorial.tax.offices', 'Tax office')
    nra_code = fields.Char('NRA code')
