# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models
from odoo.osv import expression

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
        return res + ['street', 'street2', 'city', 'function', 'company_name', 'commercial_company_name']

    @api.model
    def _get_translatable_search_fields(self):
        return ['name', 'company_name', 'commercial_company_name']

    @api.model
    def _get_active_lang_codes(self):
        return [
            lang['code']
            for lang in self.env['res.lang'].sudo().search_read([('active', '=', True)], ['code'])
        ]

    @api.model
    def _resolve_translatable_field(self, field_path):
        model = self
        field = None
        for fname in field_path.split('.'):
            field = model._fields.get(fname)
            if not field:
                return None
            if field.relational:
                model = self.env.get(field.comodel_name)
                if model is None:
                    return None
            else:
                break
        if field and field.translate and not field.relational:
            return field
        return None

    @api.model
    def _search_multi_lang(self, operator, value, field_list=None):
        if not value or not field_list:
            return []

        lang_codes = self._get_active_lang_codes()
        domains = []

        for field_name in field_list:
            field = self._fields.get(field_name)
            if not field or not field.translate:
                continue

            domains.append([(field_name, operator, value)])
            for lang_code in lang_codes:
                domains.append([(f"{field_name}.{lang_code}", operator, value)])

        return expression.OR(domains) if domains else []

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override за многоезично търсене при избор на партньор"""
        args = list(args) if args else []

        base_results = super().name_search(name=name, args=args, operator=operator, limit=limit)
        if not name:
            return base_results

        # Полетата за търсене
        search_fields = self._get_translatable_search_fields()

        # Генерираме многоезичен домейн
        multi_lang_domain = self._search_multi_lang(operator, name, search_fields)
        if not multi_lang_domain:
            return base_results

        domain = expression.AND([args, multi_lang_domain])
        records = self.search_fetch(domain, ['display_name'], limit=limit)
        extra_results = [(record.id, record.display_name) for record in records.sudo()]

        # Събиране на резултатите без дублиране, със спазване на limit.
        seen = set()
        merged = []
        for item in base_results + extra_results:
            if item[0] in seen:
                continue
            seen.add(item[0])
            merged.append(item)
            if limit and len(merged) >= limit:
                break
        return merged

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        search_fnames = list(self._rec_names_search or ([self._rec_name] if self._rec_name else []))
        if not search_fnames:
            return domain

        if not any(self._resolve_translatable_field(fname) for fname in search_fnames):
            for fname in self._get_translatable_search_fields():
                if fname not in search_fnames:
                    search_fnames.append(fname)

        lang_codes = self._get_active_lang_codes()
        if not lang_codes:
            return domain

        aggregator = expression.AND if operator in expression.NEGATIVE_TERM_OPERATORS else expression.OR
        extra_domains = []
        for field_name in search_fnames:
            field = self._resolve_translatable_field(field_name)
            if not field:
                continue
            for lang_code in lang_codes:
                extra_domains.append([(f"{field_name}.{lang_code}", operator, value)])

        if not extra_domains:
            return domain

        return aggregator([domain] + extra_domains)

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
                # Запазваме текущия език при sudo()
                current_lang = self.env.lang or 'en_US'
                parent_name = _get_lang_value(self.sudo().with_context(lang=current_lang).parent_id.name)
                name = f"{commercial or parent_name}, {name}"

        return name.strip()

    @api.depends('is_company', 'name', 'parent_id.name', 'type', 'company_name', 'commercial_company_name')
    def _compute_complete_name(self):
        # Follow core logic but keep only the language context.
        lang = self.env.lang or 'en_US'
        for partner in self:
            partner.complete_name = partner.with_context(lang=lang)._get_complete_name()
