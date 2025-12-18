#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re

from odoo.addons.partner_multilang.models.res_transliterate import partner_name_translate
from odoo.addons.partner_multilang.models.res_transliterate import LANGUAGE_MAPPING

_logger = logging.getLogger(__name__)

email_addr_escapes_re = re.compile(r'[\\"]')


def _module_installed(env, module_name: str) -> bool:
    env.cr.execute(
        """
        SELECT 1
        FROM ir_module_module
        WHERE name = %s
          AND state = 'installed' LIMIT 1
        """,
        (module_name,),
    )
    return env.cr.fetchone() is not None


def _table_exists(env, table_name: str) -> bool:
    env.cr.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = %s LIMIT 1
        """,
        (table_name,),
    )
    return env.cr.fetchone() is not None


def _ensure_project_task_translated_columns_are_jsonb(env):
    """
    Fix за Odoo 18 translate=True Char: колоните трябва да са jsonb.
    """
    if not _module_installed(env, "project"):
        _logger.info("Skip jsonb migration: module 'project' is not installed.")
        return
    if not _table_exists(env, "project_task"):
        _logger.info("Skip jsonb migration: table 'project_task' does not exist.")
        return

    table = "project_task"
    columns = ("partner_name", "partner_company_name")

    env.cr.execute(
        """
        SELECT column_name, udt_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name IN %s
        """,
        (table, columns),
    )
    udt_by_col = dict(env.cr.fetchall())

    for col in columns:
        udt = udt_by_col.get(col)
        if udt is None or udt == "jsonb":
            continue

        if udt in ("varchar", "text"):
            _logger.info("Converting %s.%s from %s to jsonb", table, col, udt)
            env.cr.execute(
                f"""
                ALTER TABLE {table}
                  ALTER COLUMN {col} TYPE jsonb
                  USING to_jsonb({col});
                """
            )
            continue

    env.cr.commit()


def _backup_partner_names(env):
    """Създава архив на имената преди Odoo да промени типа на колоната."""
    _logger.info("Creating backup of res.partner names...")
    env.cr.execute("DROP TABLE IF EXISTS backup_res_partner_names")
    env.cr.execute("""
        CREATE TABLE backup_res_partner_names AS
        SELECT id, name
        FROM res_partner
        WHERE name IS NOT NULL
    """)


def pre_init_hook(env):
    # 1. Архивираме текущите (български) имена
    _backup_partner_names(env)

    # 2. Оправяме jsonb типовете за проекта
    _ensure_project_task_translated_columns_are_jsonb(env)

    # 3. Активираме българския език, ако е архивиран
    lang = env["res.lang"].with_context(active_test=False).search(
        [("code", "=", "bg_BG"), ("active", "=", False)],
        limit=1,
    )
    if lang:
        lang.action_unarchive()


def post_init_hook(env):
    # Настройваме езиците за транслитерация
    for lang in env["res.lang"].with_context(active_test=False).search([]):
        if f"{lang.code[:2]}" in LANGUAGE_MAPPING:
            lang.transliterate = True

    # Възстановяваме българските имена от архива директно в JSONB ключа 'bg_BG'
    if _table_exists(env, "backup_res_partner_names"):
        _logger.info("Restoring Bulgarian names from backup into JSONB...")
        env.cr.execute("""
                       UPDATE res_partner p
                       SET name = COALESCE(p.name, '{}'::jsonb) ||
                                  jsonb_build_object('bg_BG', b.name) FROM backup_res_partner_names b
                       WHERE p.id = b.id
                       """)
        env.cr.execute("DROP TABLE backup_res_partner_names")

    # Оригинална логика за транслитерация (en_US)
    languages = env["res.lang"].search([("code", "!=", "en_US"), ("transliterate", "=", True)])
    partners = env["res.partner"].search([])
    for partner_id in partners.filtered(lambda r: r.name):
        # В Odoo 18 name е jsonb, затова взимаме текущата стойност за езика
        text = partner_id.with_context(lang='bg_BG').name or partner_id.name
        if isinstance(text, dict):
            text = text.get('bg_BG') or next(iter(text.values()), '')

        for lang in languages:
            transliterate_lang = partner_name_translate(text, lang.code[:2], lang.transliterate)
            _logger.info("Partner %s => %s", text, transliterate_lang)

            # Записваме преводите през ORM за сигурност
            partner_id.with_context(lang=lang.code).name = text
            partner_id.with_context(lang="en_US").name = transliterate_lang


def uninstall_hook(env):
    """
    При деинсталация извличаме Българския превод и го поставяме като
    основна стойност, преди Odoo да премахне JSONB структурата.
    """
    _logger.info("Uninstall hook: Preserving Bulgarian names...")

    env.cr.execute("""
                   SELECT udt_name
                   FROM information_schema.columns
                   WHERE table_name = 'res_partner'
                     AND column_name = 'name'
                   """)
    res = env.cr.fetchone()

    if res and res[0] == 'jsonb':
        # Извличаме bg_BG стойността. Ако я няма, взимаме каквото има.
        # Тъй като Odoo ще конвертира към varchar, ние правим JSON-а да съдържа само текст.
        env.cr.execute("""
                       UPDATE res_partner
                       SET name = to_jsonb(
                           CASE
                               WHEN name ? 'bg_BG' THEN name ->> 'bg_BG'
                               WHEN name ? 'en_US' THEN name ->> 'en_US'
                               ELSE (SELECT value FROM jsonb_each_text(name) LIMIT 1)
                END
            )
                       WHERE name IS NOT NULL;
                       """)
        _logger.info("Names successfully reverted to Bulgarian text before field conversion.")
