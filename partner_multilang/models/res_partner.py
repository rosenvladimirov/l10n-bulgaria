# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

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
    def _search_multi_lang(self, operator, value, field_list=None):
        if not value or not field_list:
            return []

        lang_codes = [l['code'] for l in self.env['res.lang'].sudo().search_read([('active', '=', True)], ['code'])]
        final_domain = []

        for field_name in field_list:
            if field_name not in self._fields or not self._fields[field_name].translate:
                continue

            # Основно търсене в текущия език
            field_domain = [(field_name, operator, value)]

            # В Odoo 18, за JSONB полета, можем да търсим в конкретни езици
            # чрез синтаксиса 'field_name.lang_code'
            for lang_code in lang_codes:
                if lang_code == self.env.lang:
                    continue  # Вече сме го покрили с основното търсене
                field_domain = ['|'] + field_domain + [(f"{field_name}.{lang_code}", operator, value)]

            if not final_domain:
                final_domain = field_domain
            else:
                final_domain = ['|'] + final_domain + field_domain

        return final_domain

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        domain = domain or []
        if name:
            # Полетата, по които искаме да търсим многоезично
            search_fields = ['name', 'company_name', 'commercial_company_name']

            # Генерираме домейна
            multi_lang_domain = self._search_multi_lang(operator, name, search_fields)

            if multi_lang_domain:
                # Внимаваме да не дублираме търсенето, ако Odoo вече е добавило името в домейна
                # Филтрираме стандартните търсения по име
                clean_domain = [
                    item for item in domain
                    if not (isinstance(item, (list, tuple)) and item[0] in search_fields)
                ]
                domain = clean_domain + multi_lang_domain

        return super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)

    def _get_complete_name(self):
        self.ensure_one()

        def _get_lang_value(field_value):
            # Ако полето е речник (JSONB превод), взимаме текущия език
            if isinstance(field_value, dict):
                lang = self.env.lang or 'en_US'
                return field_value.get(lang) or field_value.get('en_US') or next(iter(field_value.values()), '')
            return field_value or ''

        displayed_types = self._complete_name_displayed_types
        type_description = dict(self._fields['type']._description_selection(self.env))

        # Прилагаме защитата върху името
        name = _get_lang_value(self.name)

        if self.company_name or self.parent_id:
            if not name and self.type in displayed_types:
                name = type_description.get(self.type, "")
            if not self.is_company:
                # Прилагаме защитата и тук за родителските полета
                commercial = _get_lang_value(self.commercial_company_name)
                parent_name = _get_lang_value(self.sudo().parent_id.name)
                name = f"{commercial or parent_name}, {name}"

        return name.strip()
