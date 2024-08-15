# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

BG_CITY_STRUCTURE = [
    ("normal", "Settlement"),
    ("cityhall", "City Hall"),
    ("municipality", "Municipality"),
]


class CityTypes(models.Model):
    _name = "res.city.types"
    _description = "Types of settlement"
    _order = "name"

    code = fields.Char("Code", index=True)
    name = fields.Char("Name", index=True, translate=True)


class City(models.Model):
    _inherit = "res.city"

    def _domain_l10n_bg_city_hall_id(self):
        return [
            ("country_id", "=", self.country_id.id),
            ("l10n_bg_structure_type", "=", "cityhall"),
        ]

    def _domain_l10n_bg_municipality_id(self):
        return [
            ("country_id", "=", self.country_id.id),
            ("l10n_bg_structure_type", "=", "municipality"),
        ]

    l10n_bg_type_settlement_id = fields.Many2one(
        "res.city.types", string="Type of settlement"
    )
    l10n_bg_ecattu = fields.Char(
        "UCATTU",
        help="The unified classifier "
        "of administrative-territorial and territorial units",
    )
    l10n_bg_city_hall_code = fields.Char("City hall code")
    l10n_bg_city_hall_id = fields.Many2one(
        "res.city", "City Hall", domain=lambda self: self._domain_l10n_bg_city_hall_id()
    )
    l10n_bg_municipality_id = fields.Many2one(
        "res.city",
        "Municipality",
        domain=lambda self: self._domain_l10n_bg_city_hall_id(),
    )
    l10n_bg_has_tax_office = fields.Boolean("Has Tax Office")
    l10n_bg_structure_type = fields.Selection(
        string="Country Structure", selection=BG_CITY_STRUCTURE, default="normal"
    )
