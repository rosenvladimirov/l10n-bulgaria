# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, tools, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)

FIELDS_TRANSLITERATE = (
                        'res.partner,name',
                        'res.partner,street',
                        'res.partner,street_name',
                        'res.partner,street_number',
                        'res.partner,street_number2',
                        'res.partner,street_building_number',
                        'res.partner,street_floor_number',
                        'res.partner,street_sector_number',
                        'res.company,name',
                        'res.users,name',
                        'res.company,street',
                        'res.company,street2',
                        'res.company,city',
                        'res.bank,name',
                        'resource.resource,name',
                        'res.country.state,name',
                        'res.city,name',
                        'res.city.street,name',
                        'res.city.street,number',
                        'res.city.street,number2',
                        'res.city.street,bilding_number',
                        'res.city.street,floor_number',
                        'res.city.street,sector_number',
                        )

class IrTranslation(models.Model):
    _inherit = "ir.translation"

    @api.model
    def create(self, vals):
        lang = self.env.user.sudo().lang
        company = self.env.user.sudo().company_id
        if company.lang == 'bg_BG' and lang == 'bg_BG' and vals.get('name', False) in FIELDS_TRANSLITERATE:
            vals['source'] = vals['src'] = self.env.get('l10n_bg_multilang.transliterate').transliterate(vals['value'])
        return super(IrTranslation, self.sudo()).create(vals).with_env(self.env)
