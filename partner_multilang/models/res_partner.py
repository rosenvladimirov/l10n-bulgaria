# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import api, fields, models
from odoo.models import NewId
from odoo.osv import expression


class Partner(models.Model):
    _inherit = ['res.partner', 'res.transliterate.mixin']
    _name = "res.partner"
    _rec_names_search = [
        'complete_name_multilanguage',
        'email',
        'ref',
        'vat',
        'company_registry',
    ]

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
        if not self._has_complete_name_multilanguage_column():
            return res
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

    def _get_complete_name(self):
        if self.env.context.get('multilang_complete_name'):
            return super()._get_complete_name()
        if not self.id or isinstance(self.id, NewId):
            return self.with_context(lang='en_US', multilang_complete_name=True)._get_complete_name()
        if self._has_complete_name_multilanguage_column():
            value = self.with_context(lang='en_US').complete_name_multilanguage
            if value:
                return value
        return super()._get_complete_name()

    @api.model
    def _get_partner_name_lang_codes(self):
        lang_codes = self._get_active_lang_codes()
        if 'en_US' not in lang_codes:
            lang_codes.append('en_US')
        return lang_codes

    @api.depends('is_company', 'name', 'parent_id.name', 'type', 'company_name', 'commercial_company_name')
    def _compute_complete_name_multilanguage(self):
        self._update_complete_name_multilanguage()

    @api.model
    def _has_complete_name_multilanguage_column(self):
        cache_key = "_complete_name_multilang_column_exists"
        cached = getattr(self.env.registry, cache_key, None)
        if cached is not None:
            return cached
        self._cr.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'res_partner'
              AND column_name = 'complete_name_multilanguage'
            LIMIT 1
            """
        )
        exists = bool(self._cr.fetchone())
        setattr(self.env.registry, cache_key, exists)
        return exists

    def _update_complete_name_multilanguage(self):
        if self.env.context.get('skip_complete_name_multilang'):
            return
        lang_codes = self._get_partner_name_lang_codes()
        current_lang = self.env.lang or 'en_US'
        for partner in self:
            for lang_code in lang_codes:
                value = partner.with_context(
                    lang=lang_code,
                    multilang_complete_name=True,
                )._get_complete_name()
                partner.with_context(
                    lang=lang_code,
                    update_lang=True,
                    skip_complete_name_multilang=True,
                ).write({'complete_name_multilanguage': value})
            partner.complete_name_multilanguage = partner.with_context(
                lang=current_lang
            ).complete_name_multilanguage or partner.with_context(lang='en_US').complete_name_multilanguage

    @api.model
    def _get_translatable_search_fields(self):
        return [
            'complete_name_multilanguage',
            'name',
            'company_name',
            'commercial_company_name',
        ]

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
