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

    tax_code = fields.Char(string='NRA Office Code', help='The TAX Administration office code.')
    partner_id = fields.Many2one('res.partner', string='NRA Partner', required=True,
                                 ondelete="cascade")
    parent_tax_id = fields.Many2one('res.territorial.tax.offices', string='Tax Territorial Directorates', required=True)
    bank_ids = fields.One2many('res.partner.bank', 'partner_id', string='Banks',
                               domain="[('tax_office_id', '=', partner_id)]")

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals.get('partner_id'):
            self.clear_caches()
            return super(TerritorialTaxOffices, self).create(vals)
        partner = self.env['res.partner'].create({
            'name': vals['name'],
            'is_company': True,
            'customer': False,
            'email': vals.get('email'),
            'phone': vals.get('phone'),
            'website': vals.get('website'),
            'vat': vals.get('vat'),
            'street': vals.get('street'),
            'street2': vals.get('street2'),
            'zip': vals.get('zip'),
            'city': vals.get('city'),
            'state_id': vals.get('state_id'),
            'country_id': vals.get('country_id'),
        })
        vals['partner_id'] = partner.id
        self.clear_caches()
        return super(TerritorialTaxOffices, self).create(vals)


class TerritorialDirectorates(models.Model):
    _description = "bulgarian Territorial Directorates"
    _name = 'res.territorial.tax.directorates'
    _inherits = {'res.partner': 'partner_id'}

    territorial_code = fields.Char(string='NRA territorial Code', help='NRA territorial Code from bank table.')
    partner_id = fields.Many2one('res.partner', string='NRA Partner', required=True,
                                 ondelete="cascade")
    child_ids = fields.One2many('res.territorial.tax.offices', 'parent_tax_id', string='Tax offices')
    bank_ids = fields.One2many('res.partner.bank', 'territorial_tax_id', string='Banks',
                               domain="[('partner_id', '=', partner_id)]")

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals.get('partner_id'):
            self.clear_caches()
            return super(TerritorialDirectorates, self).create(vals)
        partner = self.env['res.partner'].create({
            'name': vals['name'],
            'is_company': True,
            'customer': False,
            'email': vals.get('email'),
            'phone': vals.get('phone'),
            'website': vals.get('website'),
            'vat': vals.get('vat'),
            'street': vals.get('street'),
            'street2': vals.get('street2'),
            'zip': vals.get('zip'),
            'city': vals.get('city'),
            'state_id': vals.get('state_id'),
            'country_id': vals.get('country_id'),
        })
        vals['partner_id'] = partner.id
        self.clear_caches()
        return super(TerritorialDirectorates, self).create(vals)
