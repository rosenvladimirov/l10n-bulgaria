#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re

from odoo.addons.partner_multilang.models.res_transliterate import partner_name_translate
from odoo.addons.partner_multilang.models.res_transliterate import LANGUAGE_MAPPING

_logger = logging.getLogger(__name__)

email_addr_escapes_re = re.compile(r'[\\"]')
cyrillic_re = re.compile(r"[\u0400-\u04FF]")


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
    # Без commit: инсталацията е една транзакция. Междинен commit оставяше
    # колоните jsonb при неинсталиран модул, ако инсталацията бъде прекъсната
    # (Пакит, 03.10.2026: odoo.sh убива HTTP заявката на 15-ата минута).


def _ensure_complete_name_multilanguage_column(env):
    if not _table_exists(env, "res_partner"):
        return
    env.cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'res_partner'
          AND column_name = 'complete_name_multilanguage'
        LIMIT 1
        """
    )
    if env.cr.fetchone():
        return
    _logger.info("Creating res_partner.complete_name_multilanguage column (jsonb)")
    env.cr.execute(
        'ALTER TABLE "res_partner" '
        'ADD COLUMN IF NOT EXISTS complete_name_multilanguage jsonb'
    )


def _backfill_complete_name_multilanguage(env):
    """complete_name_multilanguage за всички контрагенти с една SQL заявка.

    Същото като ``_get_complete_name_multilang`` по език: името в езика (с
    резерва en_US); лице с родител — „<име на родителя>, <име>“. ORM обхождане
    по контрагент (update_field_translations за всеки) не се побира в 15-те
    минути на HTTP заявка в odoo.sh при 26 хил. записа. Само контрагентите с
    празно име и тип адрес (там етикетът на типа е преведен) минават през ORM —
    те са малко.
    """
    _ensure_complete_name_multilanguage_column(env)
    Partner = env["res.partner"].with_context(active_test=False)
    lang_codes = Partner._get_partner_name_lang_codes()
    parts = []
    params = []
    for code in lang_codes:
        own = "COALESCE(NULLIF(p.name->>%s, ''), p.name->>'en_US', '')"
        par = "COALESCE(NULLIF(pp.name->>%s, ''), pp.name->>'en_US', '')"
        parts.append(
            "%s, btrim(CASE WHEN NOT COALESCE(p.is_company, false) AND pp.id IS NOT NULL "
            f"AND {par} <> '' THEN {par} || ', ' || {own} ELSE {own} END)"
        )
        # ключът, родителят ×2, собственото име ×2
        params += [code] * 5
    displayed = tuple(Partner._complete_name_displayed_types)
    env.cr.execute(
        f"""
        UPDATE res_partner p
           SET complete_name_multilanguage = jsonb_build_object({', '.join(parts)})
          FROM res_partner p2
          LEFT JOIN res_partner pp ON pp.id = p2.parent_id
         WHERE p2.id = p.id
           AND NOT (COALESCE(p.name->>'en_US', '') = ''
                    AND (p.parent_id IS NOT NULL OR p.company_name IS NOT NULL)
                    AND p.type IN %s)
        """,
        params + [displayed],
    )
    _logger.info("complete_name_multilanguage: %s partners by SQL", env.cr.rowcount)
    env.cr.execute(
        """
        SELECT id FROM res_partner
         WHERE COALESCE(name->>'en_US', '') = ''
           AND (parent_id IS NOT NULL OR company_name IS NOT NULL)
           AND type IN %s
        """,
        [displayed],
    )
    rest = Partner.browse([row[0] for row in env.cr.fetchall()])
    if rest:
        rest._update_complete_name_multilanguage()
        _logger.info("complete_name_multilanguage: %s address partners by ORM", len(rest))


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
                       SET name = COALESCE(p.name, '{}'::jsonb) || jsonb_build_object('bg_BG', b.name)
                       FROM backup_res_partner_names b
                       WHERE p.id = b.id
                       """)
        env.cr.execute("DROP TABLE backup_res_partner_names")

    _transliterate_partner_names(env)
    _backfill_complete_name_multilanguage(env)


def _transliterate_partner_names(env, batch_size=5000):
    """bg_BG = кирилицата, en_US = транслитерацията — за всяко кирилско име.

    Направо в SQL, не през ``write``: при българска фирма с изключена
    транслитерация (подразбирането при инсталация) ``_force_multilanguage``
    копира записаната стойност на ВСИЧКИ езици, т.е. записът на en_US
    слагаше латиницата и в bg_BG (решение на Росен 03.10.2026: кирилица в
    bg, латиница в en). Транслитерацията е същата функция в Python;
    записът е на партиди с UPDATE … FROM (VALUES …), без commit.
    """
    cr = env.cr
    cr.execute(
        """
        SELECT id, COALESCE(NULLIF(name->>'bg_BG', ''), name->>'en_US')
          FROM res_partner
         WHERE name IS NOT NULL
        """
    )
    rows = [(pid, text) for pid, text in cr.fetchall() if text and cyrillic_re.search(text)]
    done = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        values = [(pid, bg, partner_name_translate(bg, "bg", True)) for pid, bg in batch]
        placeholders = ", ".join(["(%s, %s, %s)"] * len(values))
        cr.execute(
            f"""
            UPDATE res_partner p
               SET name = COALESCE(p.name, '{{}}'::jsonb)
                          || jsonb_build_object('bg_BG', v.bg, 'en_US', v.en),
                   transliterate_tracking = COALESCE(p.transliterate_tracking, '{{}}'::jsonb)
                          || '{{"name": true}}'::jsonb
              FROM (VALUES {placeholders}) AS v(id, bg, en)
             WHERE p.id = v.id
            """,
            [item for triple in values for item in triple],
        )
        done += cr.rowcount
    _logger.info("Transliterated %s partner names (bg_BG kept, en_US latin)", done)
    env["res.partner"].invalidate_model(["name", "transliterate_tracking"])


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
