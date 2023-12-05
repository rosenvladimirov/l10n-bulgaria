#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from .iso9 import transliterate

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = 'res.company'

    def address_name_translate(self, name):
        name = super().address_name_translate(name)
        lang_name = f'display_name_{self.env.user.lang.split("_")[0]}'
        if lang_name in self.env['res.partner']._fields:
            return transliterate(name)
        return name
