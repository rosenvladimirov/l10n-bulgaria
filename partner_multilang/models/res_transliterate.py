# Part of Odoo. See LICENSE file for full copyright and licensing details.
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

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

TRANSLITERATE_FIELDS = [
    'name', 'company_name',
    'city', 'street', 'street2',
    'private_city', 'private_street', 'private_street2'
]

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
    @api.depends('name')
    def _compute_display_name(self):
        """
        Override на _compute_display_name за многоезична поддръжка.

        Одоо 19 използва display_name computed field вместо name_get().
        Този метод автоматично извлича правилния език от многоезичното name поле.
        """
        current_lang = self.env.context.get('lang') or self.env.user.lang or 'en_US'

        for record in self:
            # Проверка дали има name поле
            if 'name' not in record._fields:
                # Fallback към parent implementation
                super(ResTransliterate, record)._compute_display_name()
                continue

            # Вземи стойността на name
            name_value = record.name

            if not name_value:
                record.display_name = ''
                continue

            # Обработка на jsonb dict (translate=True jsonb колона)
            if isinstance(name_value, dict):
                # Опитай текущия език
                display = name_value.get(current_lang)

                # Fallback към en_US
                if not display:
                    display = name_value.get('en_US')

                # Fallback към първата налична стойност
                if not display and name_value:
                    try:
                        display = next(iter(name_value.values()), '')
                    except (StopIteration, AttributeError):
                        display = ''

                record.display_name = display or ''

            # Обработка на varchar string (translate=True varchar колона)
            else:
                record.display_name = str(name_value) if name_value else ''

    def _get_transliterate_languages(self):
        """
        Retrieves a list of languages that support transliteration.

        This method searches for languages in the system where the attribute
        'transliterate' is set to True.

        Returns:
            list: A list of res.lang recordsets where transliteration is enabled.
        """
        return self.env['res.lang'].search([('transliterate', '=', True)])

    def _get_code_lang(self, code):
        """
        Searches for a language based on its ISO code.

        This method looks up the language record in the system's language
        database that matches the given ISO code.

        Parameters:
            code (str): The ISO code of the language to search for.

        Returns:
            res.lang: The language record that corresponds to the given ISO code.
        """
        return self.env['res.lang'].search([('iso_code', '=', code)])

    @api.model
    def _get_transliterate_fields(self):
        """Override в конкретни модели за допълнителни полета"""
        return []

    def _check_lang(self, text):
        """
        Checks and determines the language of the given text and whether transliteration
        is supported for that language. If the current language is not recognized, attempts
        to detect the language of the text automatically.

        Parameters:
        text: str
            The text input whose language is to be checked or detected.

        Returns:
        tuple
            A tuple containing:
            - str: The determined current language code.
            - list: A filtered list of installed languages supporting transliteration.
        """
        current_lang = lang = self.env.user.lang
        installed_langs = self._get_transliterate_languages()
        transliterate = installed_langs.filtered(lambda r: r.code == lang)

        # Ако текущият език не е разпознат, опитваме автоматично разпознаване
        if not lang or lang == 'unknown':
            detected_lang = detect_text_language(text)
            if detected_lang != 'unknown':
                current_lang = detected_lang
                # Проверяваме дали разпознатият език поддържа транслитерация
                transliterate = installed_langs.filtered(
                    lambda r: r.code.startswith(detected_lang)
                )

        return current_lang, transliterate

    def _get_field_value_for_lang(self, field_name, lang=None):
        """
        Retrieves the value of a specified field for a given language. If the language
        is not provided, it defaults to the current context or user's language,
        falling back to 'en_US'.

        Parameters:
        field_name: str
            The name of the field for which the value is to be retrieved.
        lang: str, optional
            The language code. Default language will be resolved from the current
            user or context if not provided.

        Returns:
        str
            The value of the field for the specified language if available; otherwise,
            returns an empty string.
        """
        if not lang:
            lang = self.env.context.get('lang') or self.env.user.lang or 'en_US'

        if field_name not in self._fields:
            return ''

        field_value = getattr(self, field_name, None)

        if not field_value:
            return ''

        # Handle jsonb dict
        if isinstance(field_value, dict):
            return (
                    field_value.get(lang) or
                    field_value.get('en_US') or
                    next(iter(field_value.values()), '')
            )

        # Handle string
        return str(field_value) if field_value else ''

    @api.depends_context('lang')
    def _force_multilanguage(self, vals, new_record=False):
        """
            Forces multilanguage support by checking and potentially transliterating specific fields
            during record creation or update. This method ensures that certain fields have their values
            recorded in the 'en_US' language context by transliterating the data if needed.

            Parameters:
                vals (dict): Values being written to the record.
                new_record (bool): Indicates if the method is processing a new record.

            Raises:
                None

            Notes:
                - The method targets specific fields listed in the global TRANSLITERATE_FIELDS
                  collection.
                - Transliterates only when the record in 'en_US' language context is missing
                  a value for the specific field.
                - Does nothing if the field name does not exist in the model.
        """
        for field_name in [x for x in TRANSLITERATE_FIELDS if x in self._fields.keys()]:
            if field_name not in self._fields.keys():
                continue

            if not new_record:
                # Проверка дали полето е празно на en_US
                new_record = not getattr(
                    self.with_context(**dict(self.env.context, lang="en_US")),
                    field_name
                ) or self.env.context.get('force_multilanguage_update', False)

            if vals.get(field_name) and new_record:
                current_lang, transliterate = self._check_lang(vals[field_name])

                # Ако е нужна транслитерация и не е en_US
                if transliterate and current_lang != "en_US":
                    # Записваме транслитерирана версия на en_US
                    record = self.with_context(
                        **dict(self.env.context, lang="en_US", update_lang=True)
                    )
                    record.write({
                        field_name: partner_name_translate(
                            vals[field_name],
                            current_lang,
                            transliterate
                        )
                    })

    @api.model_create_multi
    def create(self, vals_list):
        """Override create за да добави многоезична поддръжка"""
        res = super().create(vals_list)
        for record, vals in zip(res, vals_list):
            record._force_multilanguage(vals, new_record=True)
        return res

    def write(self, vals):
        """Override write за да обнови многоезични стойности"""
        res = super().write(vals)
        # Избягваме безкраен цикъл с update_lang флаг
        if not self.env.context.get('update_lang', False):
            for record in self:
                record._force_multilanguage(vals, new_record=False)
        return res
