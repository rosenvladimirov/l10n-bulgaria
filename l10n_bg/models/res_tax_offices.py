# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import _

import logging
_logger = logging.getLogger(__name__)


class TaxOffices(models.Model):
    _description = "Bulgarian Tax Offices"
    _name = 'res.taxoffices'
    _inherits = {'res.partner': 'partner_id'}
    _order = 'tax_code'

    tax_code = fields.Char(string='Office Code', help='The TAX Administration office code.', required=True)
    partner_id = fields.Many2one('res.partner', string='Tax Office', required=True, )


class TerriorialDirectorates(models.Model):
    _description = "bulgarian Terriorial Directorates"
    _name = 'res.terriorialdirectorates'
    _inherits = {'res.partner': 'partner_id'}
    _order = 'terdir_code'

    terdir_code = fields.Char(string='State Code', help='The state code.', required=True)
    partner_id = fields.Many2one('res.partner', string='Tax Office', required=True, )
