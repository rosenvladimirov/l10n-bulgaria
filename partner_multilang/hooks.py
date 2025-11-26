#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models
from .models.res_transliterate import partner_name_translate
from .models.res_transliterate import LANGUAGE_MAPPING

from .odoo.models import regex_order

_logger = logging.getLogger(__name__)


def pre_init_hook(env):
    lang = env['res.lang'].with_context(active_test=False).search([('code', '=', 'bg_BG'), ('active', '=', False)])
    if lang:
        lang.toggle_active()


def post_init_hook(env):
    for lang in env['res.lang'].with_context(active_test=False).search([]):
        if f"{lang.code[:2]}" in LANGUAGE_MAPPING:
            lang.transliterate = True

    languages = env['res.lang'].search([('code', '!=', 'en_US'), ('transliterate', '=', True)])
    partners = env['res.partner'].search([])
    for partner_id in partners.filtered(lambda r: r.name):
        text = partner_id.name
        for lang in languages:
            transliterate_lang = partner_name_translate(text, lang.code[:2], lang.transliterate)
            _logger.info(f"Partner {text} => {transliterate_lang} The {lang.code} and is a transliterate language: {lang.transliterate}")
            partner_id.with_context(lang=lang.code).name = text
            partner_id.with_context(lang="en_US").name = transliterate_lang


def post_load_hook():
    models.regex_order = regex_order
