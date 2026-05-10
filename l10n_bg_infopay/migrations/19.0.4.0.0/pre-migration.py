# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Pre-migration: rename non-prefixed `infopay_*` columns on core
models to the mandatory `l10n_bg_infopay_*` prefix per
``feedback_l10n_bg_field_prefix_rule`` (project rule).

Renames are issued BEFORE Odoo's auto-update runs the registry, so
the registry sees the new column names from the start and no
phantom column creation happens.

Targeted columns:

* ``res_company.infopay_unique_id``       → ``l10n_bg_infopay_unique_id``
* ``res_company.infopay_token_user_id``   → ``l10n_bg_infopay_token_user_id``
* ``account_journal.infopay_account_id``  → ``l10n_bg_infopay_account_id``
* ``account_journal.infopay_last_sync``   → ``l10n_bg_infopay_last_sync``
* ``account_payment.infopay_payment_id``  → ``l10n_bg_infopay_payment_id``
* ``account_payment.infopay_sca_url``     → ``l10n_bg_infopay_sca_url``
* ``account_payment.infopay_status``      → ``l10n_bg_infopay_status``
* ``account_payment.infopay_bulk``        → ``l10n_bg_infopay_bulk``

Each rename is gated by an ``information_schema`` check so the
migration is re-runnable / idempotent.
"""

import logging

_logger = logging.getLogger(__name__)

RENAMES = [
    ("res_company", "infopay_unique_id", "l10n_bg_infopay_unique_id"),
    ("res_company", "infopay_token_user_id", "l10n_bg_infopay_token_user_id"),
    ("account_journal", "infopay_account_id", "l10n_bg_infopay_account_id"),
    ("account_journal", "infopay_last_sync", "l10n_bg_infopay_last_sync"),
    ("account_payment", "infopay_payment_id", "l10n_bg_infopay_payment_id"),
    ("account_payment", "infopay_sca_url", "l10n_bg_infopay_sca_url"),
    ("account_payment", "infopay_status", "l10n_bg_infopay_status"),
    ("account_payment", "infopay_bulk", "l10n_bg_infopay_bulk"),
]


def migrate(cr, version):
    if not version:
        # Fresh install — no columns to rename, the new fields will be
        # created with the correct names by Odoo's auto-update.
        return

    for table, old_col, new_col in RENAMES:
        cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = %s AND column_name = %s
            """,
            (table, old_col),
        )
        if not cr.fetchone():
            _logger.info(
                "l10n_bg_infopay 19.0.4.0.0 pre-migration: "
                "%s.%s already renamed (or never existed) — skipping.",
                table, old_col,
            )
            continue
        cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = %s AND column_name = %s
            """,
            (table, new_col),
        )
        if cr.fetchone():
            # Both columns exist — copy data old → new, drop old, to
            # let downstream registry settle on the new column.
            _logger.warning(
                "l10n_bg_infopay 19.0.4.0.0 pre-migration: both %s.%s "
                "and %s.%s exist; merging and dropping the old one.",
                table, old_col, table, new_col,
            )
            cr.execute(
                "UPDATE %s SET %s = COALESCE(%s, %s)" % (
                    table, new_col, new_col, old_col,
                )
            )
            cr.execute("ALTER TABLE %s DROP COLUMN %s" % (table, old_col))
        else:
            _logger.info(
                "l10n_bg_infopay 19.0.4.0.0 pre-migration: "
                "renaming %s.%s → %s.%s",
                table, old_col, table, new_col,
            )
            cr.execute(
                "ALTER TABLE %s RENAME COLUMN %s TO %s" % (
                    table, old_col, new_col,
                )
            )
