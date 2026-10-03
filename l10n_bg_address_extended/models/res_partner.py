# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models, tools

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = "res.partner"

    street_building_number = fields.Char(
        "Building Number",
        compute="_compute_l10n_bg_street_data",
        inverse="_inverse_l10n_bg_street_data",
        store=True,
    )
    street_floor_number = fields.Char(
        "Floor Number",
        compute="_compute_l10n_bg_street_data",
        inverse="_inverse_l10n_bg_street_data",
        store=True,
    )
    street_sector_number = fields.Char(
        "Sector Name/Number",
        compute="_compute_l10n_bg_street_data",
        inverse="_inverse_l10n_bg_street_data",
        store=True,
    )

    def _l10n_bg_compose_street(self):
        """Улицата от под-полетата — едно място за двата inverse-а."""
        self.ensure_one()
        street = ((self.street_name or "") + " " + (self.street_number or "")).strip()
        if self.street_sector_number:
            street = _("Sector: ") + self.street_sector_number + ", " + street
        if self.street_building_number:
            street = street + _(", building: ") + self.street_building_number
        if self.street_floor_number:
            street = street + _(", Floor: ") + self.street_floor_number
            # етаж без апартамент: street_number2 е False — без него
            if self.street_number2:
                street = street + ", " + self.street_number2
        elif self.street_number2:
            # без етаж — апартаментът както в base_address_extended
            street = street + " - " + self.street_number2
        return street

    def _l10n_bg_set_street(self, street):
        """Пише street само при промяна.

        Inverse-ите се викат и преди всички под-полета да са в кеша (напр.
        при запис заедно с country_id) и съставят празна улица. Празна
        стойност върху празно преводимо поле (partner_multilang) се записва
        във ВСИЧКИ езици, а следващият запис обновява само текущия език —
        така en_US оставаше празно. Непроменена стойност не се пише.
        """
        self.ensure_one()
        if street != (self.street or ""):
            self.street = street

    def _inverse_street_data(self):
        # форматът на base_address_extended, само с пазача срещу празния запис
        for partner in self:
            street = ((partner.street_name or "") + " " + (partner.street_number or "")).strip()
            if partner.street_number2:
                street = street + " - " + partner.street_number2
            partner._l10n_bg_set_street(street)

    def _inverse_l10n_bg_street_data(self):
        """update self.street based on street_name, street_number and street_number2"""
        for partner in self:
            partner._l10n_bg_set_street(partner._l10n_bg_compose_street())

    @api.depends("street")
    def _compute_l10n_bg_street_data(self):
        """Splits street value into sub-fields.
        Recomputes the fields of STREET_FIELDS when `street` of a partner is updated"""
        for partner in self:
            partner.update(tools.street_split(partner.street))

    def _get_street_split(self):
        self.ensure_one()
        res = super()._get_street_split()
        res.update(
            {
                "street_building_number": self.street_building_number,
                "street_floor_number": self.street_floor_number,
                "street_sector_number": self.street_sector_number,
            }
        )
        return res
