# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import _

import logging
_logger = logging.getLogger(__name__)


class TerritorialTaxOffices(models.Model):
    _description = "Bulgarian Tax Offices"
    _name = 'res.territorial.tax.offices'
    _inherits = {'res.partner': 'partner_id'}
    _order = 'tax_code'

    tax_code = fields.Char(string='Office Code', help='The TAX Administration office code.', required=True)
    partner_id = fields.Many2one('res.partner', string='Tax Office', required=True, )
    parent_id = fields.Many2one('res.territorial.tax.offices', string='Tax Territorial Directorates', required=True)
    bank_ids = fields.One2many('res.partner.bank', 'partner_id', string='Banks',
                               domain="[('tax_office_id', '=', partner_id)]")


class TerritorialDirectorates(models.Model):
    _description = "bulgarian Territorial Directorates"
    _name = 'res.territorial.tax.directorates'
    _inherits = {'res.partner': 'partner_id'}
    _order = 'territorial_code'

    territorial_code = fields.Char(string='State Code', help='The state code.', required=True)
    partner_id = fields.Many2one('res.partner', string='Tax Office', required=True, )
    child_ids = fields.One2many('res.territorial.tax.offices', 'parent_id', string='Tax offices')
    bank_ids = fields.One2many('res.partner.bank', 'territorial_tax_id', string='Banks',
                               domain="[('partner_id', '=', partner_id)]")
