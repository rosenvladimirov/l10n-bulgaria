#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.exceptions import UserError
from odoo.tools.translate import load_language
from odoo import _

_logger = logging.getLogger(__name__)

# Ключът по подразбиране за криптиране на blacklist.enc.
# LGPL — прозрачен. Целта е compliance signaling, не DRM.
# Ако администраторът промени ключа (ir.config_parameter → l10n_bg.blacklist_key),
# трябва да преген blacklist.enc с tools/update_blacklist.py.
_BLACKLIST_DEFAULT_KEY = 'wsONQSiUYbHkR1dI5FhEwwb_vAVlZ4WU9IovLlSqhfw='


def _init_blacklist_key(env):
    """Инициализира ключа за блекълист при инсталация или ъпгрейд."""
    ICP = env['ir.config_parameter'].sudo()
    if not ICP.get_param('l10n_bg.blacklist_key'):
        ICP.set_param('l10n_bg.blacklist_key', _BLACKLIST_DEFAULT_KEY)
        _logger.info('l10n_bg_config: blacklist key initialized in ir.config_parameter')


def pre_init_hook(env):
    # if env.user.company_id.country_code != 'BG':
    #     raise UserError(_("This module is only for Bulgaria"))
    modules = env["ir.module.module"].search([("state", "=", "installed")])
    for lang in ["base.lang_bg", "base.lang_en"]:
        res_id = env.ref(lang, raise_if_not_found=False)
        language = env["res.lang"].search(
            [("id", "=", res_id.id), ("active", "=", False)]
        )
        if language:
            load_language(env.cr, language.code)
            modules._update_translations(language.code)


def post_init_hook(env):
    env.company._inverse_is_l10n_bg_multilanguage()
    _init_blacklist_key(env)


def post_migrate_hook(env):
    """Ad-hoc hook при ъпгрейд от стари версии без блекълист."""
    _init_blacklist_key(env)
