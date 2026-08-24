# -*- coding: utf-8 -*-
"""Case-insensitive търсене за кирилица/гръцки при бази с ``LC_CTYPE=C``.

⚠️ Не е бъг на модула — базата е създадена с локал ``C``, тъй че PostgreSQL
``lower()``/``ILIKE`` сгъват само ASCII. „асими" не намира „АСИМИ".

Лекът е ICU колация: ``x COLLATE "und-x-icu" ILIKE y`` сгъва кирилицата.
Обвиваме резултата на ``registry.unaccent`` (вика се за ДВЕТЕ страни на ilike)
само докато се строи like-условие върху ПРЕВОДИМО char/text поле. Извън този
прозорец unaccent си работи както обикновено — не пипаме нищо друго.

Guard: колацията ``und-x-icu`` (ICU) съществува от PostgreSQL 10+ с ICU. Ако
липсва, оставяме поведението на ядрото (по-добре case-sensitive, отколкото
счупено търсене).
"""
import logging

from odoo.orm import fields
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

_ICU_COLLATION = "und-x-icu"
_orig_condition_to_sql = fields.Field._condition_to_sql


def _condition_to_sql(self, field_expr, operator, value, model, alias, query):
    # Само like-операторите върху преводими текстови полета имат нужда.
    if (
        isinstance(operator, str)
        and operator.endswith("like")
        and getattr(self, "translate", False)
        and self.type in ("char", "text")
    ):
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
            return _orig_condition_to_sql(
                self, field_expr, operator, value, model, alias, query
            )
        original_unaccent = registry.unaccent

        def _collated(sql):
            # Колацията се слага ВЪРХУ резултата на unaccent (или на самата
            # стойност, ако unaccent е изключен). Двете страни на ilike
            # получават една и съща колация → PostgreSQL я ползва за сгъването.
            return SQL('%s COLLATE "%s"', original_unaccent(sql), SQL(_ICU_COLLATION))

        registry.unaccent = _collated
        try:
            return _orig_condition_to_sql(
                self, field_expr, operator, value, model, alias, query
            )
        finally:
            registry.unaccent = original_unaccent

    return _orig_condition_to_sql(self, field_expr, operator, value, model, alias, query)


fields.Field._condition_to_sql = _condition_to_sql
_logger.info("partner_multilang: ICU-collation search patch applied (und-x-icu)")
