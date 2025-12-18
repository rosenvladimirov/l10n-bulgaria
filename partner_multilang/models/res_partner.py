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

        lang_codes = self.env['res.lang'].sudo().search_read([('active', '=', True)], ['code'])
        final_domain = []

        for field_name in field_list:
            if field_name not in self._fields or not self._fields[field_name].translate:
                continue

            # Създаваме група от условия за конкретното поле (OR между езиците)
            field_domain = [(field_name, operator, value)]
            for lang in lang_codes:
                field_domain = ['|'] + field_domain + [(f"{field_name}.{lang['code']}", operator, value)]

            # Добавяме към общия домейн с OR спрямо останалите полета
            if not final_domain:
                final_domain = field_domain
            else:
                final_domain = ['|'] + final_domain + field_domain

        return final_domain

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        if not name:
            return super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)

        domain = domain or []
        default_fields = {'name', 'company_name', 'commercial_company_name'}

        # 1. Генерираме многоезичния домейн
        multi_lang_domain = self._search_multi_lang(operator, name, list(default_fields))

        # 2. Филтрираме оригиналния домейн, за да премахнем стандартните търсения по име,
        # които Odoo добавя автоматично, за да не се дублират с нашето.
        clean_domain = []
        for item in domain:
            if isinstance(item, (list, tuple)) and len(item) >= 3 and item[0] in default_fields:
                continue
            clean_domain.append(item)

        # 3. Комбинираме: (всичко от clean_domain) AND (нашият multi_lang_domain)
        # Odoo автоматично добавя '&' между елементите в списъка
        final_domain = clean_domain + [multi_lang_domain] if multi_lang_domain else clean_domain

        return super()._name_search(
            name='', domain=final_domain, operator=operator, limit=limit, order=order
        )

    def _get_complete_name(self):
        self.ensure_one()

        def _as_lang_str(value):
            if isinstance(value, dict):
                lang = (self.env.context or {}).get("lang") or "en_US"
                return value.get(lang) or value.get("en_US") or next(iter(value.values()), "") or ""
            return value or ""

        displayed_types = self._complete_name_displayed_types
        type_description = dict(self._fields["type"]._description_selection(self.env))

        name = _as_lang_str(self.name)
        if self.company_name or self.parent_id:
            if not name and self.type in displayed_types:
                name = type_description[self.type]
            if not self.is_company:
                parent_name = _as_lang_str(self.sudo().parent_id.name)
                commercial = _as_lang_str(self.commercial_company_name)
                name = f"{commercial or parent_name}, {name}"
        return (name or "").strip()
