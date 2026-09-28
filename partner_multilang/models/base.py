# -*- coding: utf-8 -*-
"""Индексите и сортирането на преводимите полета — за всички модели.

1. ``init()``: за всяко преводимо поле с ``index='trigram'`` създава сгънат
   trigram индекс, огледален на предфилтъра от ``search_collation_patch``.
   Без него сгънатото търсене е коректно, но минава с пълно сканиране.
2. ``_order_field_to_sql()``: ``ORDER BY`` на преводимо текстово поле получава
   ICU колацията на езика на потребителя. Ядрото сортира по колацията на базата
   (``C``) — по кодова точка, т.е. „асими“ след „Бяла“, „Ä“ след „z“.

Заменя предишния ``base.py``, който не беше вписан в ``models/__init__.py``
и никога не се зареждаше.
"""
from odoo import api, models
from odoo.tools import SQL

from .collation import ensure_fold_trigram_index, order_collation


class Base(models.AbstractModel):
    _inherit = "base"

    @api.private
    def init(self):
        super().init()
        if self._abstract or not self._auto or self._table_query:
            return
        for field in self._fields.values():
            if (
                field.translate
                and field.store
                and field.index == "trigram"
                and field.column_type
                and not field.inherited
            ):
                ensure_fold_trigram_index(self.env, self, field)

    @api.model
    def _order_field_to_sql(self, alias, field_name, direction, nulls, query):
        field = self._fields.get(field_name)  # само прости имена, без „x.y“
        if (
            field is not None
            and field.translate
            and field.type in ("char", "text")
            and field.store
            and field.column_type
            and not self.env.context.get("prefetch_langs")
        ):
            collation = order_collation(self.env, self.env.lang or "en_US")
            if collation:
                sql_field = SQL(
                    '%s COLLATE "%s"',
                    self._field_to_sql(alias, field_name, query),
                    SQL(collation),
                )
                # Същият израз и в GROUP BY/DISTINCT — иначе PostgreSQL отказва.
                query._order_groupby.append(sql_field)
                return SQL("%s %s %s", sql_field, direction, nulls)
        return super()._order_field_to_sql(alias, field_name, direction, nulls, query)
