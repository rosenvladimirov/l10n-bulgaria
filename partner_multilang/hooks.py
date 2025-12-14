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
           AND state = 'installed'
         LIMIT 1
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
           AND table_name = %s
         LIMIT 1
        """,
        (table_name,),
    )
    return env.cr.fetchone() is not None


def _ensure_project_task_translated_columns_are_jsonb(env):
    """
    Fix за Odoo 18 translate=True Char: колоните трябва да са jsonb.
    Спира грешката: COALESCE types character varying and jsonb cannot be matched
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

        if udt is None:
            _logger.info("Skip column migration: %s.%s does not exist.", table, col)
            continue

        if udt == "jsonb":
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

        raise ValueError(f"Unexpected DB type for {table}.{col}: {udt}")


def pre_init_hook(env):
    # ВАЖНО: оправя типа преди инсталация/upgrade да стигне до flush/write
    _ensure_project_task_translated_columns_are_jsonb(env)

    lang = env["res.lang"].with_context(active_test=False).search(
        [("code", "=", "bg_BG"), ("active", "=", False)],
        limit=1,
    )
    if lang:
        lang.action_unarchive()


def post_init_hook(env):
    for lang in env["res.lang"].with_context(active_test=False).search([]):
        if f"{lang.code[:2]}" in LANGUAGE_MAPPING:
            lang.transliterate = True

    languages = env["res.lang"].search([("code", "!=", "en_US"), ("transliterate", "=", True)])
    partners = env["res.partner"].search([])
    for partner_id in partners.filtered(lambda r: r.name):
        text = partner_id.name
        for lang in languages:
            transliterate_lang = partner_name_translate(text, lang.code[:2], lang.transliterate)
            _logger.info(
                "Partner %s => %s The %s and is a transliterate language: %s",
                text, transliterate_lang, lang.code, lang.transliterate,
            )
            partner_id.with_context(lang=lang.code).name = text
            partner_id.with_context(lang="en_US").name = transliterate_lang
