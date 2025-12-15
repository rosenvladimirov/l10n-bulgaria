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
        """
        Constructs a domain for multi-language search by considering translatable fields and
        language-specific translations. If no value or field list is provided, it returns an
        empty domain. The method dynamically searches through JSONB translations for all
        active languages configured in the system.

        :param operator: The comparison operator for the search condition (e.g., '=', 'ilike').
        :type operator: str
        :param value: The value to search for in the specified fields.
        :type value: Any
        :param field_list: A list of field names where the search will be conducted. Fields
            must be marked as translatable to be considered.
        :type field_list: list[str] | None
        :return: A domain that can be used in searches to filter records based on multi-language
            criteria.
        :rtype: list
        """
        if not value or not field_list:
            return []

        domain = []

        # Кеширане на езиковите кодове, за да избегнем многократни DB заявки
        lang_codes = self.env['res.lang'].sudo().search_read([('active', '=', True)], ['code'])
        lang_codes = [lang['code'] for lang in lang_codes]

        for field_name in field_list:
            if field_name in self._fields and self._fields[field_name].translate:
                if not domain:
                    domain = [(field_name, operator, value)]
                else:
                    domain = ['|'] + domain + [(field_name, operator, value)]

                # Добавяме търсене в JSONB превода за всеки език
                for lang_code in lang_codes:
                    domain = ['|'] + domain + [(f"{field_name}->>'{lang_code}'", operator, value)]

        return domain

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        """
        Search for records using the name and provided domain, operator, limit, and order parameters.
        The method enhances the multi-language search capability by identifying fields in the domain
        that need to be translated and applies the corresponding multi-language search logic. If
        no translation fields are found, it defaults to certain predefined fields. The method builds
        a combined domain for performing multi-language search in conjunction with the provided domain.

        :param name: The name by which to search.
        :param domain: Additional domain filters for the search.
        :type domain: list or None
        :param operator: The operator to be used in the search criteria.
        :param limit: The maximum number of records to return.
        :type limit: int
        :param order: The order of the results returned.
        :return: A list of record identifiers matching the search criteria.
        :rtype: list
        """
        if not name:
            return super(Partner, self)._name_search(name=name, domain=domain, operator=operator, limit=limit,
                                                     order=order)

        domain = domain or []

        # Извличаме полетата, които вече са в домейна за търсене
        search_fields = set()
        default_fields = {'name', 'company_name', 'commercial_company_name'}

        for item in domain:
            if isinstance(item, (list, tuple)) and len(item) >= 3 and item[1] == operator and isinstance(item[0], str):
                field = item[0]
                # Премахваме оператори за JSONB ако има такива
                if '->>' in field:
                    field = field.split('->>')[0]
                # Добавяме полето към списъка с полета за търсене
                if field in self._fields and self._fields[field].translate:
                    search_fields.add(field)

        # Ако не са намерени полета в домейна, използваме стандартните полета
        if not search_fields:
            search_fields = default_fields

        # Създаваме домейн за многоезично търсене
        multi_lang_domain = self._search_multi_lang(operator, name, list(search_fields))

        # Премахваме оригиналните условия за търсене в полетата, които ще бъдат заменени с многоезични
        new_domain = []
        for item in domain:
            if not (isinstance(item, (list, tuple)) and len(item) >= 3 and
                    item[1] == operator and isinstance(item[0], str) and
                    (item[0] in search_fields or item[0].split('->>')[0] in search_fields)):
                new_domain.append(item)

        # Комбинираме с многоезичните условия
        if multi_lang_domain:
            if new_domain:
                # Използваме AND между съществуващия домейн и новия многоезичен домейн
                domain = ['&'] * (len(new_domain) - 1) + new_domain + multi_lang_domain
            else:
                domain = multi_lang_domain
        else:
            domain = new_domain

        return super(Partner, self)._name_search(
            name='', domain=domain, operator=operator, limit=limit, order=order
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
