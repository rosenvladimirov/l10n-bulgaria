# -*- coding: utf-8 -*-
"""Колации и индекси за преводимите полета.

Базите на Odoo се създават с колация ``C`` (commit 276ea81 в ядрото). Там
PostgreSQL ``lower()``/``ILIKE`` сгъват само ASCII, а сортирането е по кодова
точка: „асими“ излиза след „Бяла“, „Ä“ — след „z“.

ICU колацията решава и двете, но само ако ИЗРАЗЪТ в заявката съвпада с израза
на индекса — включително колацията. Затова тук държим на едно място:

* ``fold()`` — сгъването за търсене: ``lower(<unaccent>(x) COLLATE "und-x-icu")``.
  Същата функция строи и заявката, и индекса.
* ``order_collation()`` — колацията за сортиране по езика на потребителя.
* ``ensure_fold_trigram_index()`` / ``ensure_order_index()`` — индексите.

Измерено на PostgreSQL 17, локал C, 200 000 партньора (28.09.2026):

* търсене „асими транс оод“: ядрото — 0 резултата; ``COLLATE`` без индекс —
  коректно, 240 ms (пълно сканиране); сгънат израз + сгънат индекс — коректно,
  0,84 ms (Bitmap Index Scan);
* ``ORDER BY … COLLATE "bg-x-icu" LIMIT 80``: 278 ms без индекс, 0,7 ms с индекс
  по същия израз.
"""
import logging
import re

from odoo.modules.db import FunctionStatus
from odoo.tools import SQL, sql

_logger = logging.getLogger(__name__)

FOLD_COLLATION = "und-x-icu"

# Кодът на езика влиза в текста на индекса — допускаме само формата на res.lang.
_LANG_RE = re.compile(r"^[A-Za-z]{2,3}(_[A-Za-z0-9]+)?(@[A-Za-z]+)?$")


def _collations(env):
    """Множеството ICU колации в базата — чете се веднъж на регистър."""
    registry = env.registry
    names = getattr(registry, "_partner_multilang_icu_collations", None)
    if names is None:
        env.cr.execute("SELECT collname FROM pg_collation WHERE collprovider = 'i'")
        names = frozenset(row[0] for row in env.cr.fetchall())
        registry._partner_multilang_icu_collations = names
    return names


def has_fold(env):
    return FOLD_COLLATION in _collations(env)


def fold(registry, expr):
    """Сгънат израз за търсене — еднакъв за заявката и за индекса."""
    return SQL('lower(%s COLLATE "%s")', registry.unaccent(expr), SQL(FOLD_COLLATION))


def order_collation(env, lang):
    """ICU колацията за сортиране на езика ``lang`` или None.

    ``bg_BG`` → ``bg-BG-x-icu`` → ``bg-x-icu`` → ``und-x-icu`` (коренът на
    Unicode — пак по-добре от ``C``).
    """
    names = _collations(env)
    if not names or not lang:
        return None
    code = lang.split("@")[0]
    parts = code.split("_")
    candidates = []
    if len(parts) > 1:
        candidates.append(f"{parts[0]}-{parts[1]}-x-icu")
    candidates += [f"{parts[0]}-x-icu", FOLD_COLLATION]
    return next((c for c in candidates if c in names), None)


def _unaccent_is_indexable(registry):
    """Индекс с unaccent има смисъл само ако функцията е IMMUTABLE — както в ядрото."""
    return registry.has_unaccent == FunctionStatus.INDEXABLE


def ensure_fold_trigram_index(env, model, field):
    """Trigram индекс върху сгънатия текст на всички преводи на полето.

    Изразът е огледален на предфилтъра, който ядрото строи в
    ``BaseString.condition_to_sql`` и който ``search_collation_patch`` сгъва.
    """
    registry = env.registry
    if not (registry.has_trigram and has_fold(env)):
        return False
    if registry.has_unaccent and not _unaccent_is_indexable(registry):
        # Заявката ще вика неиндексируем unaccent — индексът няма да се ползва.
        _logger.warning(
            "partner_multilang: unaccent не е IMMUTABLE — сгънатият индекс за %s.%s не се създава",
            model._table, field.name,
        )
        return False
    indexname = sql.make_identifier(f"{model._table}__{field.name}_pm_fold")
    if sql.index_exists(env.cr, indexname):
        return False
    column = f"""(jsonb_path_query_array("{field.name}", '$.*')::text)"""
    if registry.has_unaccent:
        column = f"unaccent({column})"
    expression = f'(lower({column} COLLATE "{FOLD_COLLATION}")) gin_trgm_ops'
    sql.create_index(env.cr, indexname, model._table, [expression], "gin")
    _logger.info("partner_multilang: създаден %s", indexname)
    return True


def ensure_order_index(env, model, fname, lang):
    """Btree индекс за ``ORDER BY <поле> COLLATE <ICU>`` на езика ``lang``.

    Изразът повтаря ``BaseString.to_sql`` на ядрото: ``COALESCE(x->>lang, x->>'en_US')``,
    а за en_US — само ``x->>'en_US'``.
    """
    if not _LANG_RE.match(lang or ""):
        return False
    collation = order_collation(env, lang)
    if not collation:
        return False
    suffix = lang.replace("@", "_").lower()
    indexname = sql.make_identifier(f"{model._table}__{fname}_{suffix}_pm_order")
    if sql.index_exists(env.cr, indexname):
        return False
    if lang == "en_US":
        value = f""""{fname}"->>'en_US'"""
    else:
        value = f"""COALESCE("{fname}"->>'{lang}', "{fname}"->>'en_US')"""
    expression = f'({value} COLLATE "{collation}")'
    sql.create_index(env.cr, indexname, model._table, [expression], "btree")
    _logger.info("partner_multilang: създаден %s", indexname)
    return True
