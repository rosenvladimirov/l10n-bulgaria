# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """
    Ensure translated Char fields are stored as jsonb in PostgreSQL.
    Fixes: COALESCE types character varying and jsonb cannot be matched
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    table = "project_task"
    columns = ("partner_name", "partner_company_name")

    env.cr.execute(
        """
        SELECT column_name, data_type, udt_name
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name IN %s
        """,
        (table, columns),
    )
    colinfo = {row[0]: (row[1], row[2]) for row in env.cr.fetchall()}

    for col in columns:
        data_type, udt_name = colinfo.get(col, (None, None))
        # Already correct
        if udt_name == "jsonb":
            continue

        # Convert common string types to jsonb
        if udt_name in ("varchar", "text"):
            env.cr.execute(
                f"""
                ALTER TABLE {table}
                  ALTER COLUMN {col} TYPE jsonb
                  USING to_jsonb({col});
                """
            )
            continue

        # If the column is missing or some unexpected type, fail loudly:
        raise ValueError(
            f"Unexpected DB type for {table}.{col}: data_type={data_type}, udt_name={udt_name}"
        )
