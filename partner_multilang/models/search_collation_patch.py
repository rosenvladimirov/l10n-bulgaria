# -*- coding: utf-8 -*-
"""Case-insensitive търсене за кирилица/гръцки при бази с ``LC_CTYPE=C``.

⚠️ Не е бъг на модула — базата е създадена с локал ``C``, тъй че PostgreSQL
``lower()``/``ILIKE`` сгъват само ASCII. „софия" не намира „СОФИЯ".

Лекът е ICU колация: ``x COLLATE "und-x-icu" ILIKE y`` сгъва кирилицата.
Измерено на PostgreSQL 17 с локал ``C``::

    lower('СОФИЯ')                     → 'СОФИЯ'   (нищо не се сгъва)
    lower('СОФИЯ' COLLATE "und-x-icu") → 'софия'   ✅
    'СОФИЯ' ILIKE '%софия%'                                  → f
    ('СОФИЯ' COLLATE "und-x-icu") ILIKE '%софия%'            → t  ✅

🚨🚨 ОБВИВАМЕ ``BaseString.condition_to_sql``, НЕ ``Field._condition_to_sql``.

Изглежда като дреболия, но е разликата между „работи" и „връща нула". За
преводимо поле ядрото строи ДВЕ условия, свързани с ``AND``::

    unaccent(jsonb_path_query_array(name,'$.*')::text) ILIKE unaccent(%s)  ← предфилтър
    AND unaccent(COALESCE(name->>'bg_BG', ...)) ILIKE unaccent(%s)         ← базово

Редът е ключов: ``BaseString.condition_to_sql`` първо вика ``super()`` (там се
ражда базовото условие), а тригам-предфилтъра строи СЛЕД това, четейки наново
``model.env.registry.unaccent``. Ако подменим unaccent само около вътрешния
``_condition_to_sql``, колацията стига до базовото условие, но предфилтърът
остава без нея — а те са свързани с ``AND``, тъй че несгънатият предфилтър
занулява целия резултат. Търсенето изглежда „пачнато" (COLLATE Е в SQL-а!) и
пак връща 0. Измерено на erp3, 24.08.2026: ``ilike 'софия'`` → 0 при 9 попадения
за ``'София'``.

Обвиването на външния метод държи прозореца отворен и за двете условия.

Guard: колацията ``und-x-icu`` (ICU) съществува от PostgreSQL 10+ с ICU. Ако
липсва, оставяме поведението на ядрото (по-добре case-sensitive, отколкото
счупено търсене).
"""
import logging

from odoo.tools import SQL

_logger = logging.getLogger(__name__)

_ICU_COLLATION = "und-x-icu"


def _install():
    """Закача пача върху най-външния метод, който строи условието.

    Връща описание за лога; при непозната структура на ядрото не пипа нищо —
    по-добре заварено поведение, отколкото счупен SQL.
    """
    try:
        from odoo.orm import fields_textual
    except ImportError:  # pragma: no cover — друга серия на Odoo
        _logger.warning("partner_multilang: няма odoo.orm.fields_textual — пачът не е сложен")
        return None

    target = getattr(fields_textual, "BaseString", None)
    orig = getattr(target, "condition_to_sql", None) if target is not None else None
    if orig is None:  # pragma: no cover — сменена структура на ядрото
        _logger.warning("partner_multilang: BaseString.condition_to_sql липсва — пачът не е сложен")
        return None

    def condition_to_sql(self, field_expr, operator, value, model, alias, query):
        # Само like-операторите върху преводими текстови полета имат нужда.
        if not (
            isinstance(operator, str)
            and operator.endswith("like")
            and getattr(self, "translate", False)
            and self.type in ("char", "text")
        ):
            return orig(self, field_expr, operator, value, model, alias, query)

        registry = model.env.registry
        # Guard: активираме COLLATE само ако ICU колацията я има в тази база.
        # Кешираме проверката на регистъра — прави се веднъж.
        has_icu = getattr(registry, "_partner_multilang_has_icu", None)
        if has_icu is None:
            model.env.cr.execute(
                "SELECT 1 FROM pg_collation WHERE collname = %s LIMIT 1",
                (_ICU_COLLATION,),
            )
            has_icu = bool(model.env.cr.fetchone())
            registry._partner_multilang_has_icu = has_icu
        if not has_icu:
            return orig(self, field_expr, operator, value, model, alias, query)

        original_unaccent = registry.unaccent

        def _collated(sql):
            # Колацията се слага ВЪРХУ резултата на unaccent (или на самата
            # стойност, ако unaccent е изключен). Двете страни на ilike
            # получават една и съща колация → PostgreSQL я ползва за сгъването.
            return SQL('%s COLLATE "%s"', original_unaccent(sql), SQL(_ICU_COLLATION))

        registry.unaccent = _collated
        try:
            return orig(self, field_expr, operator, value, model, alias, query)
        finally:
            registry.unaccent = original_unaccent

    target.condition_to_sql = condition_to_sql
    return "%s.condition_to_sql" % target.__name__


_installed = _install()
if _installed:
    _logger.info(
        "partner_multilang: ICU-collation search patch applied (%s, %s)",
        _installed, _ICU_COLLATION,
    )
