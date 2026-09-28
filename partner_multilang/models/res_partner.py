# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import re

from lxml import etree

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL

from .collation import ensure_order_index, fold, has_fold

_NEGATIVE_TERM_OPERATORS = ('!=', '<>', 'not in', 'not like', 'not ilike')
# Полетата, по които се сортират списъците — индекс за сортиране по всеки активен език.
_ORDER_INDEX_FIELDS = ('complete_name_multilanguage', 'name')

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = ['res.partner', 'res.transliterate.mixin']
    _name = "res.partner"
    # Ядрото сортира по complete_name — то се смята винаги на en_US (латиница).
    # Сортираме по преводимото пълно име на езика на потребителя; ICU колацията
    # и индексът за нея идват от base.py / collation.py.
    _order = "complete_name_multilanguage ASC, id DESC"

    name = fields.Char(translate=True, index='trigram')
    street = fields.Char(translate=True)
    street2 = fields.Char(translate=True)
    city = fields.Char(translate=True)
    function = fields.Char(translate=True)
    company_name = fields.Char(translate=True)
    commercial_company_name = fields.Char(translate=True)
    # index=True се игнорира от ядрото за преводимо поле (приема само trigram) —
    # досега полето, по което търсим, нямаше никакъв индекс.
    complete_name_multilanguage = fields.Char(
        compute='_compute_complete_name_multilanguage',
        store=True,
        index='trigram',
        translate=True,
    )

    @property
    def _rec_names_search(self):
        return list(set(["complete_name_multilanguage"] + super()._rec_names_search))

    @api.private
    def init(self):
        super().init()
        # Ensure the technical JSONB column exists without module upgrade.
        # Odoo 19: self._cr е deprecated → използваме self.env.cr.
        self.env.cr.execute(
            'ALTER TABLE "res_partner" '
            'ADD COLUMN IF NOT EXISTS complete_name_multilanguage jsonb'
        )
        self._pm_ensure_order_indexes()

    @api.model
    def _pm_ensure_order_indexes(self, lang_codes=None):
        """Btree индекс за ORDER BY <поле> COLLATE <ICU> по всеки активен език."""
        if lang_codes is None:
            lang_codes = [code for code, _name in self.env['res.lang'].get_installed()]
        for lang in lang_codes:
            for fname in _ORDER_INDEX_FIELDS:
                ensure_order_index(self.env, self, fname, lang)

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
        domain = super()._search_display_name(operator, value)
        domain = self._strip_lang_suffix_in_domain(domain)
        search_fnames = list(self._rec_names_search or ([self._rec_name] if self._rec_name else []))
        if not search_fnames:
            return domain

        if not any(self._resolve_translatable_field(fname) for fname in search_fnames):
            for fname in self._get_translatable_search_fields():
                if fname not in search_fnames:
                    search_fnames.append(fname)

        # Само собствени съхранени колони: по тях строим SQL върху всички преводи.
        fields_ = [
            self._fields[fname] for fname in dict.fromkeys(search_fnames)
            if fname in self._fields and self._resolve_translatable_field(fname)
            and self._fields[fname].store and not self._fields[fname].inherited
        ]
        if not fields_:
            return domain

        query = self.with_context(active_test=False)._search([])
        condition = self._pm_any_translation_condition(
            query.table, fields_, self._positive_search_operator(operator), value,
        )
        if condition is None:
            return domain
        query.add_where(condition)

        if operator in _NEGATIVE_TERM_OPERATORS:
            return Domain.AND([domain, [('id', 'not in', query)]])
        return Domain.OR([domain, [('id', 'in', query)]])

    @api.model
    def _pm_any_translation_condition(self, alias, fields_, operator, value):
        """SQL условие „съвпада в който и да е превод“ — една заявка, по индекса.

        Досега търсенето правеше по едно ``search()`` за всяко поле и всеки език
        (N×M заявки) и слагаше резултата в огромен ``id IN (...)``. Тук всички
        преводи се четат наведнъж през ``jsonb_path_query_array(поле, '$.*')`` —
        същия израз, върху който е trigram индексът.

        * ``ilike``: сгънат израз (``collation.fold``) → сгънатия индекс;
        * ``like``: без сгъване → индекса на ядрото;
        * ``=``/``in``: предфилтър по индекса + точна проверка по всеки превод;
        * ``=like``/``=ilike``: точна проверка по всеки превод (без индекс).

        Връща None за неподдържан оператор/стойност — тогава остава домейнът на ядрото.
        """
        registry = self.env.registry
        folding = has_fold(self.env)
        values = [value] if isinstance(value, str) else value
        if not values or not all(isinstance(v, str) for v in values):
            return None

        def all_langs(fname):
            return SQL("jsonb_path_query_array(%s, '$.*')::text", SQL.identifier(alias, fname))

        def json_pattern(text, exact=False):
            # Стойностите в масива са JSON-екранирани („ → \"), затова екранираме
            # и шаблона — както value_to_translated_trigram_pattern в ядрото.
            escaped = re.sub(r'(_|%|\\)', r'\\\1', json.dumps(text, ensure_ascii=False)[1:-1])
            return f'%"{escaped}"%' if exact else f'%{escaped}%'

        def ci(left, right):
            # Case-insensitive сравнение по индекса, ако има ICU; иначе ILIKE на ядрото.
            if folding:
                return SQL("%s LIKE %s", fold(registry, left), fold(registry, SQL("%s", right)))
            return SQL("%s ILIKE %s", registry.unaccent(left), registry.unaccent(SQL("%s", right)))

        conditions = []
        for field in fields_:
            column = SQL.identifier(alias, field.name)
            if operator == 'ilike':
                conditions.append(ci(all_langs(field.name), json_pattern(values[0])))
            elif operator == 'like':
                conditions.append(SQL(
                    "%s LIKE %s", registry.unaccent(all_langs(field.name)),
                    registry.unaccent(SQL("%s", json_pattern(values[0]))),
                ))
            elif operator in ('=', 'in'):
                # unaccent и в двете страни — за да съвпадне с индекса на ядрото;
                # точната проверка след това отсява излишното.
                prefilter = SQL(" OR ").join(
                    SQL(
                        "%s LIKE %s", registry.unaccent(all_langs(field.name)),
                        registry.unaccent(SQL("%s", json_pattern(v, exact=True))),
                    )
                    for v in values
                )
                conditions.append(SQL(
                    "((%s) AND EXISTS (SELECT 1 FROM jsonb_each_text(%s) t WHERE t.value IN %s))",
                    prefilter, column, tuple(values),
                ))
            elif operator in ('=ilike', '=like'):
                cmp_op = SQL("ILIKE") if operator == '=ilike' else SQL("LIKE")
                if operator == '=ilike' and folding:
                    cmp = SQL("%s LIKE %s", fold(registry, SQL("t.value")), fold(registry, SQL("%s", values[0])))
                else:
                    cmp = SQL("t.value %s %s", cmp_op, values[0])
                conditions.append(SQL(
                    "EXISTS (SELECT 1 FROM jsonb_each_text(%s) t WHERE %s)", column, cmp,
                ))
            else:
                return None
        return SQL("(%s)", SQL(" OR ").join(conditions))

    @api.model
    def _get_translatable_search_fields(self):
        return [
            'complete_name_multilanguage',
            'name',
            'company_name',
            'commercial_company_name',
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
    def _strip_lang_suffix_in_domain(self, domain):
        if not domain:
            return domain
        lang_codes = set(self._get_active_lang_codes())
        context_lang = self.env.context.get('lang')
        if context_lang:
            lang_codes.add(context_lang)
        user_lang = self.env.user.lang
        if user_lang:
            lang_codes.add(user_lang)
        if not lang_codes:
            return domain

        def _strip(tokens):
            cleaned = []
            for token in tokens:
                if isinstance(token, (list, tuple)) and len(token) >= 3:
                    field_name = token[0]
                    if isinstance(field_name, str) and '.' in field_name:
                        base, suffix = field_name.split('.', 1)
                        if suffix in lang_codes:
                            field = self._fields.get(base)
                            if field and field.translate and not field.relational:
                                token = (base,) + tuple(token[1:])
                    cleaned.append(token)
                elif isinstance(token, list):
                    cleaned.append(_strip(token))
                else:
                    cleaned.append(token)
            return cleaned

        return _strip(domain)

    @api.model
    def _positive_search_operator(self, operator):
        if operator in ('not ilike', 'not like'):
            return operator[4:]
        if operator in ('!=', '<>'):
            return '='
        if operator == 'not in':
            return 'in'
        return operator

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
