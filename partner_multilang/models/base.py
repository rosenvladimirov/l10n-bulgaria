# partner_multilang/models/base_model.py
# -*- coding: utf-8 -*-
import logging
from odoo import api, models
from odoo.tools.sql import SQL

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _order_to_sql(self, order, query, alias=None, reverse=False):
        """
        Override ORDER BY to use current user language for translate fields.

        Wraps translate field ordering with COALESCE to handle:
        1. Current user language (e.g., 'bg_BG')
        2. Fallback to 'en_US'
        3. Fallback to varchar cast (if column is not jsonb)
        """
        sql_order = super()._order_to_sql(order, query, alias, reverse)

        if not sql_order:
            return sql_order

        # Get current language
        lang = self.env.context.get('lang') or self.env.user.lang or 'en_US'

        # Quick check - if no ->> in result, nothing to modify
        sql_str = str(sql_order)
        if '->>' not in sql_str:
            return sql_order

        # Check which fields in order are translate fields
        translate_fields = []
        for part in order.split(','):
            field_name = part.strip().split()[0]
            if field_name in self._fields:
                field_obj = self._fields[field_name]
                if getattr(field_obj, 'translate', False) and field_obj.type == 'char':
                    translate_fields.append(field_name)

        if not translate_fields:
            return sql_order

        # Modify SQL for each translate field
        import re
        modified_sql = sql_str
        table_alias = alias or self._table

        for field_name in translate_fields:
            # Pattern: "alias"."field"->>'any_lang'
            # We need to capture the full field reference
            pattern = rf'("{re.escape(table_alias)}"\."{re.escape(field_name)}")->>\'[^\']+\''

            def build_coalesce(match):
                field_ref = match.group(1)  # "table"."field"
                return (
                    f"COALESCE("
                    f"{field_ref}->>\'{lang}\', "
                    f"{field_ref}->>\'en_US\', "
                    f"{field_ref}::text"
                    f")"
                )

            modified_sql = re.sub(pattern, build_coalesce, modified_sql)

        if modified_sql != sql_str:
            _logger.debug(
                f"ORDER BY modified for {self._name}: using language '{lang}'"
            )
            return SQL(modified_sql)

        return sql_order
