#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import load_language
from odoo import _

_logger = logging.getLogger(__name__)

# Кодът на нашия standalone cron (служи за идемпотентно намиране — записът
# се създава програмно, без XML id, за да можем да го трием при uninstall).
_REGISTER_CRON_CODE = 'model._l10n_bg_push_registration()'
_REGISTER_CRON_NAME = 'l10n_bg: Push registered clients'
# Стандартният Odoo „нотифи" cron (mail) — закачаме се за него ако е наличен.
_PUBLISHER_CRON_XMLID = 'mail.ir_cron_module_update_notification'

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


def _find_own_cron(env):
    """Намира нашия standalone registration cron (по код+модел)."""
    return env['ir.cron'].sudo().with_context(active_test=False).search([
        ('model_id', '=', env.ref('base.model_res_company').id),
        ('code', '=', _REGISTER_CRON_CODE),
    ], limit=1)


def _hide_cron_from_menu(env, cron, hide=True):
    """Прилага същата хватка като mail: добавя/маха cron-а в exclude
    domain-а на Scheduled Actions менюто (``base.ir_cron_act``), за да не
    се вижда в Settings → Technical → Scheduled Actions.
    """
    act = env.ref('base.ir_cron_act', raise_if_not_found=False)
    if not act:
        return
    domain = safe_eval(act.domain or '[]') if isinstance(act.domain, str) else list(act.domain or [])
    norm = [tuple(x) if isinstance(x, (list, tuple)) else x for x in domain]
    clause = ('id', '!=', cron.id)
    has = clause in norm
    if hide and not has:
        norm.append(clause)
    elif not hide and has:
        norm.remove(clause)
    else:
        return
    act.sudo().domain = repr([list(c) if isinstance(c, tuple) else c for c in norm])


def _setup_registration_cron(env):
    """Закача регистрационния push към EE/publisher „нотифи" cron, или
    прави собствен СКРИТ cron ако publisher cron-ът липсва.

    * publisher cron наличен → push-ът минава през ``update_notification``
      override-а (виж models/publisher_warranty.py); НЕ държим собствен
      cron (трием го ако е останал от mail-less състояние).
    * publisher cron липсва (mail-less) → създаваме собствен седмичен cron
      и го скриваме от менюто със същата domain-хватка като mail.
    """
    publisher_cron = env.ref(_PUBLISHER_CRON_XMLID, raise_if_not_found=False)
    own = _find_own_cron(env)
    if publisher_cron:
        if own:
            _hide_cron_from_menu(env, own, hide=False)
            own.sudo().unlink()
        return
    if not own:
        own = env['ir.cron'].sudo().create({
            'name': _REGISTER_CRON_NAME,
            'model_id': env.ref('base.model_res_company').id,
            'state': 'code',
            'code': _REGISTER_CRON_CODE,
            'user_id': env.ref('base.user_root').id,
            'interval_number': 1,
            'interval_type': 'weeks',
        })
    _hide_cron_from_menu(env, own, hide=True)


def post_init_hook(env):
    env.company._inverse_is_l10n_bg_multilanguage()
    _init_blacklist_key(env)
    _setup_registration_cron(env)
    # Самата инсталация инжектира {vat, name} на bus канал l10n-bulgaria.
    env.company._l10n_bg_push_registration()


def uninstall_hook(env):
    """Чисти след себе си: маха standalone cron-а и domain-хватката."""
    own = _find_own_cron(env)
    if own:
        _hide_cron_from_menu(env, own, hide=False)
        own.sudo().unlink()


# Upgrade-time setup (cron wiring) lives in migrations/<version>/post-migrate.py
# — stock Odoo does not honor a 'post_migrate_hook' manifest key, only
# OpenUpgrade does. post_init_hook runs only on fresh install.
