#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

# Библиотеки за транслитерация
try:
    from transliterate import translit

    HAS_TRANSLITERATE = True
except ImportError:
    HAS_TRANSLITERATE = False

from unidecode import unidecode

# Библиотеки за разпознаване на език
try:
    from lingua import Language, LanguageDetectorBuilder

    # Създаваме детектор за поддържаните езици
    SUPPORTED_LANGUAGES = [
        Language.BULGARIAN, Language.ENGLISH, Language.RUSSIAN,
        Language.SERBIAN, Language.MACEDONIAN, Language.UKRAINIAN
    ]
    LINGUA_DETECTOR = LanguageDetectorBuilder.from_languages(*SUPPORTED_LANGUAGES).build()
    HAS_LINGUA = True
except ImportError:
    HAS_LINGUA = False

try:
    from langdetect import detect

    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False

from lxml import etree
from odoo import api, models

_logger = logging.getLogger(__name__)
TRANSLITERATE_FIELDS = ['name', 'company_name',
                        'city', 'street', 'street2',
                        'private_city', 'private_street', 'private_street2']

# Маппинг за езикови кодове
LANGUAGE_MAPPING = {
    'bg': 'bg',  # Български
    'ru': 'ru',  # Руски
    'mk': 'mk',  # Македонски
    'sr': 'sr',  # Сръбски
    'uk': 'uk',  # Украински
    'be': 'be',  # Беларуски
}


def detect_text_language(text):
    """Разпознава езика на текста с приоритет на библиотеките"""
    if not text or len(text.strip()) < 3:
        return 'unknown'

    # Приоритет 1: Lingua (най-точна)
    if HAS_LINGUA:
        try:
            language = LINGUA_DETECTOR.detect_language_of(text)
            if language:
                return language.iso_code_639_1.name.lower()
        except Exception as e:
            _logger.warning(f"Lingua detection failed: {e}")

    # Приоритет 2: langdetect (бърза)
    if HAS_LANGDETECT:
        try:
            return detect(text)
        except Exception as e:
            _logger.warning(f"Langdetect failed: {e}")

    return 'unknown'


def partner_name_translate(name, lang, transliterate_flag):
    """Транслитерира имена с автоматично разпознаване на език"""
    if lang not in ["en", "en_US"] and transliterate_flag:
        # Ако няма зададен език, опитваме се да го разпознаем
        if not lang or lang == 'unknown':
            detected_lang = detect_text_language(name)
            if detected_lang != 'unknown':
                lang = detected_lang

        lang_code = lang[:2] if lang else 'unknown'

        # Опитваме специфична транслитерация по език
        if HAS_TRANSLITERATE and lang_code in LANGUAGE_MAPPING:
            try:
                return translit(name, LANGUAGE_MAPPING[lang_code], reversed=True)
            except Exception as e:
                _logger.warning(f"Transliterate failed for {lang_code}: {e}")

        # Fallback към Unidecode
        return unidecode(name)
    return name


class ResTransliterate(models.AbstractModel):
    _name = "res.transliterate.mixin"
    _description = "Names transliterate mixin"

    @api.depends_context('lang')
    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        lang_order = f"name->>'{self.env.user.lang}'"
        result = super(ResTransliterate, self).get_view(
            view_id=view_id, view_type=view_type, **options
        )
        value_fields = self.fields_get()
        if value_fields.get('name') and value_fields['name']['type'] == 'char' \
                and not value_fields['name'].get('related') and view_type in ["tree", "kanban"]:
            doc = etree.XML(result["arch"])
            for type_in in ["tree", "kanban"]:
                for node in doc.xpath(f"//{type_in}"):
                    node.set("default_order", lang_order)
            result["arch"] = etree.tostring(doc, encoding="unicode")
        return result

    def _get_transliterate_languages(self):
        return self.env['res.lang'].search([('transliterate', '=', True)])

    def _get_code_lang(self, code):
        return self.env['res.lang'].search([('iso_code', '=', code)])

    @api.model
    def _get_transliterate_fields(self):
        return []

    def _check_lang(self, text):
        current_lang = lang = self.env.user.lang
        installed_langs = self._get_transliterate_languages()
        transliterate = installed_langs.filtered(lambda r: r.code == lang)

        # Ако текущият език не е разпознат, опитваме автоматично разпознаване
        if not lang or lang == 'unknown':
            detected_lang = detect_text_language(text)
            if detected_lang != 'unknown':
                current_lang = detected_lang
                # Проверяваме дали разпознатият език поддържа транслитерация
                transliterate = installed_langs.filtered(lambda r: r.code.startswith(detected_lang))

        return current_lang, transliterate

    @api.depends_context('lang')
    def _force_multilanguage(self, vals, new_record=False):
        for field_name in [x for x in TRANSLITERATE_FIELDS if x in self._fields.keys()]:
            if field_name not in self._fields.keys():
                continue
            if not new_record:
                new_record = not getattr(self.with_context(**dict(self._context, lang="en_US")), field_name)
            # _logger.info(f'New record: {new_record} {getattr(self.with_context(**dict(self._context, lang="en_US")), field_name)}')
            if vals.get(field_name) and new_record:
                current_lang, transliterate = self._check_lang(vals[field_name])
                # # Save in user lang
                # record = self.with_context(**dict(self._context, lang=current_lang, update_lang=True))
                # record.write({
                #   field_name: vals[field_name],
                # })
                # if transliterate save transliterated
                if transliterate and current_lang != "en_US":
                    record = self.with_context(**dict(self._context, lang="en_US", update_lang=True))
                    record.write({
                        field_name: partner_name_translate(vals[field_name], current_lang, transliterate)
                    })

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record, vals in zip(res, vals_list):
            record._force_multilanguage(vals, new_record=True)
        return res

    def write(self, vals):
        res = super().write(vals)
        if not self._context.get('update_lang', False):
            for record in self:
                record._force_multilanguage(vals, new_record=False)
        return res
