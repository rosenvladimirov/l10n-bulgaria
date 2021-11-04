# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _


class Company(models.Model):
    _inherit = ["res.company"]
    _name = "res.company"

    street_building_number = fields.Char('Bulding Number', compute='_compute_address',
                              inverse='_inverse_street_building_number', translate=True)
    street_floor_number = fields.Char('Floor Number', compute='_compute_address',
                              inverse='_inverse_street_floor_number', translate=True)
    street_sector_number = fields.Char('Sector Number', compute='_compute_address',
                              inverse='_inverse_street_sector_number', translate=True)

    address_invoice = fields.Many2one(compute="_get_invoice_address", comodel_name='res.partner')

    @api.multi
    def get_formated_street(self):
        for company in self:
            if company.partner_id:
                partner = company.partner_id
                street_format = (partner.country_id.street_format or
                    '%(street_number)s/%(street_number2)s %(street_name)s')
                args = {}
                for field in partner.get_street_fields():
                    args[field] = getattr(self, field) or ''
        return street_format % args

    @api.depends('partner_id')
    def _get_invoice_address(self):
        for company in self:
            company.address_invoice = company.partner_id.address_get(['invoice'])['invoice']

    def _get_company_address_fields(self, partner):
        address_fields = super(Company, self)._get_company_address_fields(partner)
        address_fields.update({
            'street_building_number': partner.street_building_number,
            'street_floor_number': partner.street_floor_number,
            'street_sector_number': partner.street_sector_number,
        })
        return address_fields

    def _inverse_street_building_number(self):
        for company in self:
            company.partner_id.street_building_number = company.street_building_number

    def _inverse_street_floor_number(self):
        for company in self:
            company.partner_id.street_floor_number = company.street_floor_number

    def _inverse_street_sector_number(self):
        for company in self:
            company.partner_id.street_sector_number = company.street_sector_number
