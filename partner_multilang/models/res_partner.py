# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from lxml import etree

from odoo import api, fields, models
from odoo.fields import Domain

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
    complete_name_multilanguage = fields.Char(
        compute='_compute_complete_name_multilanguage',
        store=True,
        index=True,
        translate=True,
    )

    @property
    def _rec_names_search(self):
        return list(set(["complete_name_multilanguage"] + super()._rec_names_search))

    @api.private
    def init(self):
        super().init()
        # Ensure the technical JSONB column exists without module upgrade.
        self._cr.execute(
            'ALTER TABLE "res_partner" '
            'ADD COLUMN IF NOT EXISTS complete_name_multilanguage jsonb'
        )

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        try:
            node = etree.fromstring(res.get('arch', ''))
        except Exception:
            return res

        changed = False
        for field_node in node.xpath(".//field[@name='complete_name']"):
            field_node.set('name', 'complete_name_multilanguage')
            changed = True

        if not changed:
            return res

        res['arch'] = etree.tostring(node, encoding="unicode").replace('\t', '')

        models = {model: set(fields) for model, fields in res.get('models', {}).items()}
        if self._name in models:
            models[self._name].add('complete_name_multilanguage')
            res['models'] = {model: tuple(fields) for model, fields in models.items()}
        return res

    @api.model
    def _get_transliterate_fields(self):
        res = super()._get_transliterate_fields()
        return res + ['street', 'street2', 'city', 'function', 'company_name', 'commercial_company_name']

    @api.model
    def _get_partner_name_lang_codes(self):
        lang_codes = self._get_active_lang_codes()
        if 'en_US' not in lang_codes:
            lang_codes.append('en_US')
        return lang_codes

    @api.depends('is_company', 'name', 'parent_id.name', 'type', 'company_name', 'commercial_company_name')
    def _compute_complete_name_multilanguage(self):
        self._update_complete_name_multilanguage()

    def _get_complete_name_multilang(self, lang):
        self.ensure_one()
        displayed_types = self._complete_name_displayed_types
        type_description = dict(self._fields['type']._description_selection(self.env))

        record = self.with_context(lang=lang)
        name = record.name or ''

        if record.company_name or record.parent_id:
            if not name and record.type in displayed_types:
                name = type_description.get(record.type, "")
            if not record.is_company:
                parent = record.sudo().parent_id
                parent_name = parent.with_context(lang=lang).name if parent else ''
                name = f"{parent_name}, {name}" if parent_name else name

        return (name or '').strip()

    def _update_complete_name_multilanguage(self):
        if self.env.context.get('skip_complete_name_multilang'):
            return
        lang_codes = self._get_partner_name_lang_codes()
        for partner in self:
            translations = {
                lang_code: partner._get_complete_name_multilang(lang_code)
                for lang_code in lang_codes
            }
            partner.update_field_translations('complete_name_multilanguage', translations)

    @api.model
    def _search_display_name(self, operator, value):
        """
        Override за многоезично търсене.
        Търси във ВСИЧКИ езици на translate=True полетата.
        """
        negative_operators = ('!=', 'not like', 'not ilike', 'not in')

        if not value and operator not in ('=', '!='):
            return [(0, '=', 1)] if operator in negative_operators else [(1, '=', 1)]

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
                domains.append([(f'{field_name}.display_name', operator, value)])
            elif getattr(field, 'translate', False):
                # Преводимо поле - търси във всички езици
                lang_domains = []
                for lang in active_langs:
                    lang_code = lang['code']
                    lang_domains.append((f"{field_name}.{lang_code}", operator, value))
                # Обединяваме с OR за всички езици на едно поле
                if lang_domains:
                    domains.append(lang_domains)
            elif operator.endswith('like'):
                # Обикновено поле
                domains.append([(field_name, operator, value)])

        if not domains:
            return [(0, '=', 1)]

        # Комбинираме всички домейни с OR или AND в зависимост от оператора
        if operator in negative_operators:
            return Domain.AND(domains)
        else:
            return Domain.OR(domains)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_complete_name_multilanguage()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('skip_complete_name_multilang'):
            return res
        trigger_fields = {
            'name',
            'company_name',
            'commercial_company_name',
            'parent_id',
            'is_company',
            'type',
        }
        if trigger_fields.intersection(vals.keys()):
            self._update_complete_name_multilanguage()
        return res
