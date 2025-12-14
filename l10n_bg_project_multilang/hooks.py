# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def _ensure_project_task_translated_columns_are_jsonb(cr):
    """
    Convert project_task.partner_name and partner_company_name to jsonb if needed.
    Must run BEFORE module init/upgrade to avoid COALESCE(varchar, jsonb) errors.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    table = "project_task"
    columns = ("partner_name", "partner_company_name")

    env.cr.execute(
        """
        SELECT column_name, udt_name
          FROM information_schema.columns
         WHERE table_name = %s
           AND column_name IN %s
        """,
        (table, columns),
    )
    udt_by_col = dict(env.cr.fetchall())

    for col in columns:
        udt = udt_by_col.get(col)

        # Column missing? Then it's not our problem to migrate here.
        if udt is None:
            continue

        if udt == "jsonb":
            continue

        if udt in ("varchar", "text"):
            # Safe here because table/col are fixed constants (not user input)
            env.cr.execute(
                f"""
                ALTER TABLE {table}
                  ALTER COLUMN {col} TYPE jsonb
                  USING to_jsonb({col});
                """
            )
            continue

        raise ValueError(f"Unexpected DB type for {table}.{col}: {udt}")


def pre_init_hook(cr):
    _ensure_project_task_translated_columns_are_jsonb(cr)


def post_init_hook(cr, registry):
    # Optional: keep as a safety net for fresh installs
    _ensure_project_task_translated_columns_are_jsonb(cr)
