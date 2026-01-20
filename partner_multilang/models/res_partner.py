# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models
from odoo.osv.expression import Domain

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = ['res.partner', 'res.transliterate.mixin']
    _name = "res.partner"

    name = fields.Char(translate=True, index='trigram')
    street = fields.Char(translate=True)
    street2 = fields.Char(translate=True)
    city = fields.Char(translate=True)
    function = fields.Char(translate=True)
    company_name = fields.Char(translate=True)
    commercial_company_name = fields.Char(translate=True)

    @api.model
    def _get_transliterate_fields(self):
        res = super()._get_transliterate_fields()
        return res + ['name', 'street', 'street2', 'city', 'function', 'company_name', 'commercial_company_name']

    @api.model
    def _search_display_name(self, operator, value):
        """
        Override за многоезично търсене.
        Търси във ВСИЧКИ езици на translate=True полетата.
        """
        if not value and operator not in ('=', '!='):
            return Domain.TRUE if operator in Domain.NEGATIVE_OPERATORS else Domain.FALSE

        # Полета за търсене (от _rec_names_search или _rec_name)
        search_fnames = self._rec_names_search or ([self._rec_name] if self._rec_name else [])
        if not search_fnames:
            return super()._search_display_name(operator, value)

        # Вземаме всички активни езици
        active_langs = self.env['res.lang'].sudo().search_read(
            [('active', '=', True)],
            ['code']
        )

        if not active_langs:
            return super()._search_display_name(operator, value)

        # Създаваме OR домейн за всички полета и езици
        aggregator = Domain.AND if operator in Domain.NEGATIVE_OPERATORS else Domain.OR
        domains = []

        for field_name in search_fnames:
            # поддръжка на вложени полета (partner_id.name)
            model = self
            field = None

            for fname in field_name.split('.'):
                field = model._fields.get(fname)
                if not field:
                    break
                if field.relational:
                    model = self.env.get(field.comodel_name)

            if not field:
                # Невалидно поле - пропускаме го
                continue

            if field.relational:
                # Релационно поле - търси в display_name
                domains.append(Domain(field_name + '.display_name', operator, value))
            elif getattr(field, 'translate', False):
                # Преводимо поле - търси във всички езици
                lang_domains = []
                for lang in active_langs:
                    lang_code = lang['code']
                    lang_domains.append(Domain(f"{field_name}.{lang_code}", operator, value))
                # Обединяваме с OR за всички езици на едно поле
                if lang_domains:
                    domains.append(Domain.OR(lang_domains))
            elif operator.endswith('like'):
                # Обикновено поле
                domains.append(Domain(field_name, operator, value))

        return aggregator(domains) if domains else Domain.FALSE
