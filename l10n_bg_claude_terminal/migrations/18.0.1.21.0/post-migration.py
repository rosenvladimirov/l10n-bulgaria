# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Migrate AI Tokenizer config from res.users to res.company.

Ran post-init защото новите полета на res.company трябва да съществуват.
Старите колони на res_users все още са в базата (Odoo не ги drop-ва
автоматично при премахване на field от модела) — четем ги директно с SQL.
В края drop-ваме колоните за чистота.
"""

import logging

_logger = logging.getLogger(__name__)

USER_FIELDS = (
    "claude_qdrant_url",
    "claude_qdrant_api_key",
    "claude_qdrant_collection_prefix",
    "claude_ollama_url",
    "claude_ollama_model",
    "claude_embedding_provider",
    "claude_embedding_api_key",
)


def migrate(cr, version):
    # Провери дали изобщо има стари колони (свеж install → няма).
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'res_users'
           AND column_name = ANY(%s)
        """,
        (list(USER_FIELDS),),
    )
    existing = {row[0] for row in cr.fetchall()}
    if not existing:
        _logger.info("claude_terminal migration 1.21.0: no legacy user columns, skipping")
        return

    # Вземи първата ненулева стойност per поле от admin-ски потребители.
    # base.group_system дава админската група; НЕ разчитай на id=2 защото
    # може да е демо/импорт.
    cols_sql = ", ".join(
        f"(SELECT u.{c} FROM res_users u "
        f"   JOIN res_groups_users_rel r ON r.uid = u.id "
        f"   JOIN ir_model_data d ON d.res_id = r.gid "
        f"  WHERE d.module='base' AND d.name='group_system' "
        f"    AND u.{c} IS NOT NULL AND u.{c} <> '' "
        f"  ORDER BY u.id LIMIT 1) AS {c}"
        for c in existing
    )
    cr.execute(f"SELECT {cols_sql}")
    row = cr.fetchone()
    if not row or not any(row):
        _logger.info("claude_terminal migration 1.21.0: no legacy values set, skipping copy")
    else:
        payload = {c: v for c, v in zip(existing, row) if v}
        _logger.info(
            "claude_terminal migration 1.21.0: copying %s field(s) to main company: %s",
            len(payload),
            sorted(payload.keys()),
        )
        # Пиши на main company (id=1) само полета които все още нямат стойност
        # (за да не презапишем ръчно зададени company стойности).
        for field, value in payload.items():
            cr.execute(
                f"UPDATE res_company SET {field} = %s "
                f" WHERE id = 1 AND ({field} IS NULL OR {field} = '')",
                (value,),
            )

    # Drop старите колони — не пречат функционално но са мъртви данни.
    for col in existing:
        cr.execute(f'ALTER TABLE res_users DROP COLUMN IF EXISTS "{col}"')
    _logger.info("claude_terminal migration 1.21.0: dropped %s legacy column(s)", len(existing))
