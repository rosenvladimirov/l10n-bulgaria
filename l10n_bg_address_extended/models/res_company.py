# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools


class Company(models.Model):
    _inherit = ["res.company"]

    street_name = fields.Char(
        "Street Name",
        compute="_compute_address",
        inverse="_inverse_street_name",
    )
    street_number = fields.Char(
        "House",
        compute="_compute_address",
        inverse="_inverse_street_number",
    )
    street_number2 = fields.Char(
        "Door",
        compute="_compute_address",
        inverse="_inverse_street_number2",
    )
    street_building_number = fields.Char(
        "Building Number",
        compute="_compute_address",
        inverse="_inverse_street_building_number",
    )
    street_floor_number = fields.Char(
        "Floor Number",
        compute="_compute_address",
        inverse="_inverse_street_floor_number",
    )
    street_sector_number = fields.Char(
        "Sector Number",
        compute="_compute_address",
        inverse="_inverse_street_sector_number",
    )
    city_id = fields.Many2one(comodel_name="res.city", string="City ID")
    country_enforce_cities = fields.Boolean(related='partner_id.country_id.enforce_cities')

    def _get_company_address_field_names(self):
        return list(set((super()._get_company_address_field_names() + ["street_name", "street_number", "street_number2", "street_building_number", "street_floor_number", "street_sector_number"])))


    def _inverse_street_name(self):
        for company in self:
            company.partner_id.street_name = company.street_name

    def _inverse_street_number(self):
        for company in self:
            company.partner_id.street_number = company.street_number

    def _inverse_street_number2(self):
        for company in self:
            company.partner_id.street_number2 = company.street_number2

    def _inverse_street_building_number(self):
        for company in self:
            company.partner_id.street_building_number = company.street_building_number

    def _inverse_street_floor_number(self):
        for company in self:
            company.partner_id.street_floor_number = company.street_floor_number

    def _inverse_street_sector_number(self):
        for company in self:
            company.partner_id.street_sector_number = company.street_sector_number


    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            self.partner_id.city_id = self.city_id
            self.city = self.city_id.name
            self.zip = self.city_id.zipcode
            self.state_id = self.city_id.state_id
        elif self._origin:
            self.partner_id.city_id = False
            self.partner_id.city = False
            self.partner_id.zip = False
            self.partner_id.state_id = False
