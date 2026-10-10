#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import load_language
from odoo import Command, _

_logger = logging.getLogger(__name__)

# Кодът на нашия standalone cron (служи за идемпотентно намиране — записът
# се създава програмно, без XML id, за да можем да го трием при uninstall).
_REGISTER_CRON_CODE = 'model._l10n_bg_push_registration()'
_REGISTER_CRON_NAME = 'l10n_bg: Push registered clients'
# Стандартният Odoo „нотифи" cron (mail) — закачаме се за него ако е наличен.
_PUBLISHER_CRON_XMLID = 'mail.ir_cron_module_update_notification'


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


_BLACKLIST_DEFAULT_KEY = 'wsONQSiUYbHkR1dI5FhEwwb_vAVlZ4WU9IovLlSqhfw='


def _init_blacklist_key(env):
    ICP = env['ir.config_parameter'].sudo()
    if not ICP.get_param('l10n_bg.blacklist_key'):
        ICP.set_param('l10n_bg.blacklist_key', _BLACKLIST_DEFAULT_KEY)


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
    """Осигурява авто-push на регистрацията.

    * EE/publisher cron наличен **И активен** → разчитаме на него (push-ът
      минава през ``update_notification`` override-а); НЕ държим собствен
      cron (трием го ако е останал).
    * publisher cron липсва **ИЛИ е изключен** → правим собствен **активен**
      СКРИТ cron — авто-push-ът е задължителен, не зависи от чужд (често
      изключен) publisher cron.
    """
    publisher_cron = env.ref(_PUBLISHER_CRON_XMLID, raise_if_not_found=False)
    own = _find_own_cron(env)
    if publisher_cron and publisher_cron.active:
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
            'active': True,
        })
    else:
        own.sudo().write({'active': True})
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


# ---------------------------------------------------------------------------
# ВОП с частичен данъчен кредит: връщане към данъка от ядрото l10n_bg
# ---------------------------------------------------------------------------

# Данъкът за ВОП с ЧДК от официалния l10n_bg, който модулът до 19.0.8.16.0
# презаписваше в data/template/account.tax-bg.csv като група.
ICA_PTC_TAX = 'l10n_bg_purchase_vat_20_ptc_ica'
# Децата на старата група. Не се трият — по тях може да има осчетоводени редове.
ICA_PTC_OLD_CHILDREN = ('l10n_bg_sale_vat_20_ica', 'l10n_bg_purchase_vat_20_ica_ptc')


def _core_ica_ptc_template(env):
    """Редът на данъка от CSV-то на ядрото l10n_bg, с таговете вече като id-та.

    Четем директно файла на l10n_bg (а не слетите данни на шаблона), за да не
    влязат в миграцията промени на плъгините l10n_bg_config_plugins_*.
    """
    chart = env['account.chart.template']
    data = chart._parse_csv('bg', 'account.tax', module='l10n_bg')
    tax_vals = data.get(ICA_PTC_TAX)
    if not tax_vals:
        return None
    chart._deref_account_tags('bg', {ICA_PTC_TAX: tax_vals})
    return tax_vals


def fix_ica_ptc_group(env, companies=None):
    """Връща ``l10n_bg_purchase_vat_20_ptc_ica`` към данъка от ядрото ``l10n_bg``.

    До 19.0.8.16.0 модулът презаписваше данъка като група от две деца
    (``l10n_bg_sale_vat_20_ica`` и ``l10n_bg_purchase_vat_20_ica_ptc``) с
    клиринг през сметка 430, като начисленият ДДС отиваше с таг 21. По
    справка-декларацията (ППЗДДС, Приложение № 13 към чл. 116, ал. 1) кл. 21 е
    „Начислен ДДС“ по облагаемите доставки 20 %, а начисленият ДДС за ВОП е в
    кл. 22 („Начислен ДДС за ВОП и за получени доставки по чл. 82, ал. 2 - 6“);
    основата е в кл. 12. Данъкът при ВОП е изискуем от придобиващия (ЗДДС,
    чл. 84), а кредитът е по чл. 69, ал. 1, т. 3 / чл. 73 срещу протокол по
    чл. 117, ал. 1, т. 1 (чл. 71, т. 5). Данъкът в ядрото прави точно това:
    основа 12_1 и 32, +100 % по 4531 с таг 42, -100 % по 4532 с таг 22.

    За всяка фирма с шаблон ``bg``, при която данъкът още е група:

    * групата става ``percent`` 20 % с разпределението от ядрото (старите
      редове на разпределение се трият, новите се създават);
    * описанието и етикетът върху фактурата се връщат към тези от ядрото;
    * старите деца се архивират (``active=False``), не се трият.

    Осчетоводените редове не се пипат. Повторното пускане не прави нищо.
    Ако по редовете на разпределение на самата група има осчетоводени
    редове (не би трябвало — групата не носи свои данъчни редове), фирмата се
    пропуска с предупреждение в лога.

    :return: поправените данъци (``account.tax``)
    """
    Tax = env['account.tax'].with_context(active_test=False)
    fixed = Tax.browse()
    if companies is None:
        companies = env['res.company'].search([('chart_template', '=', 'bg')])
    if not companies:
        return fixed
    core = _core_ica_ptc_template(env)
    if not core:
        _logger.warning("l10n_bg_config: %s is missing in l10n_bg; nothing to fix", ICA_PTC_TAX)
        return fixed

    for company in companies:
        chart = env['account.chart.template'].with_company(company)
        tax = chart.ref(ICA_PTC_TAX, raise_if_not_found=False)
        if not tax or tax.amount_type != 'group':
            continue

        old_lines = tax.repartition_line_ids
        if old_lines and env['account.move.line'].sudo().search_count(
            [('tax_repartition_line_id', 'in', old_lines.ids)], limit=1,
        ):
            _logger.warning(
                "l10n_bg_config: company %s: the repartition lines of %s are used by journal items; "
                "the tax was left unchanged, fix it manually", company.id, ICA_PTC_TAX)
            continue

        # Новото разпределение — по реда на CSV-то на ядрото; сметките са xml id
        new_lines = []
        missing_account = False
        for command in core.get('repartition_line_ids', []):
            vals = dict(command[2])
            if vals.get('account_id'):
                account = chart.ref(vals['account_id'], raise_if_not_found=False)
                if not account:
                    missing_account = vals['account_id']
                    break
                vals['account_id'] = account.id
            new_lines.append(Command.create(vals))
        if missing_account:
            _logger.warning(
                "l10n_bg_config: company %s: account %s not found; %s was left unchanged",
                company.id, missing_account, ICA_PTC_TAX)
            continue

        children = tax.children_tax_ids
        tax.write({
            'amount_type': core.get('amount_type', 'percent'),
            'amount': core.get('amount', 20.0),
            'children_tax_ids': [Command.clear()],
            'repartition_line_ids': [Command.delete(line.id) for line in old_lines] + new_lines,
        })
        # Текстовете от ядрото; старият превод на описанието („0% ДДС - ВОП“) е грешен
        texts = {f: core[f] for f in ('description', 'invoice_label') if core.get(f)}
        if texts:
            tax.with_context(lang='en_US').write(texts)
        if 'description' in texts:
            # Описанието е html_translate; при запис на en_US старият превод
            # оцелява по термини. Ядрото няма превод на това описание, затова
            # оставяме само en_US и другите езици падат към него. Първо
            # flush — иначе отложеният запис на ORM връща старите езици.
            tax.flush_recordset(['description'])
            env.cr.execute(
                "UPDATE account_tax SET description = jsonb_build_object('en_US', description->'en_US')"
                " WHERE id = %s AND description IS NOT NULL",
                (tax.id,),
            )
            tax.invalidate_recordset(['description'])

        old_children = children
        for xmlid in ICA_PTC_OLD_CHILDREN:
            old_children |= chart.ref(xmlid, raise_if_not_found=False) or Tax.browse()
        old_children.filtered('active').write({'active': False})

        fixed |= tax
        _logger.info(
            "l10n_bg_config: company %s: %s restored from l10n_bg; archived %s",
            company.id, ICA_PTC_TAX, old_children.ids)
    return fixed
