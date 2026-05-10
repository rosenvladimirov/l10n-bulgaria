"""Pre-migration for 18.0.5.0.0.

Drops two columns whose security boundary has changed:

* ``res_company.l10n_bg_infopay_unique_id``        — was a plain Char.
  The uniqueId is paired with the access token; both must sit on the
  same security boundary.  Moves to the user crypto wallet (encrypted
  with the user's password hash).  After upgrade, operators must
  re-call ``_infopay_set_credentials(uid, tok)`` to re-populate.

* ``res_company.l10n_bg_infopay_admin_unique_id``  — was a plain Char.
  The admin uniqueId now lives Fernet-encrypted in the new column
  ``l10n_bg_infopay_admin_unique_id_encrypted`` (auto-created by
  Odoo when the new module loads).  Operators must re-call
  ``_l10n_bg_infopay_set_admin_credentials(uid, tok)``.

We do NOT auto-migrate ciphertext: the user wallet needs a password
that this script does not have, and the admin Fernet ciphertext is
fine where it is — only the new uniqueId column needs to be filled.
Re-setting credentials is the safe path; logs warn the operator.
"""

import logging

_logger = logging.getLogger(__name__)


COLUMNS_TO_DROP = [
    ("res_company", "l10n_bg_infopay_unique_id"),
    ("res_company", "l10n_bg_infopay_admin_unique_id"),
]


def migrate(cr, version):
    if not version:
        return

    for table, column in COLUMNS_TO_DROP:
        cr.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = %s",
            (table, column),
        )
        if not cr.fetchone():
            continue
        # Warn operators about non-empty values that will be discarded.
        cr.execute(
            "SELECT COUNT(*) FROM {table} WHERE {column} IS NOT NULL "
            "AND {column} != ''".format(table=table, column=column)
        )
        non_empty = cr.fetchone()[0]
        if non_empty:
            _logger.warning(
                "InfoPay 18.0.5.0.0: dropping %s.%s with %s non-empty "
                "value(s).  Re-set InfoPay credentials after upgrade "
                "to repopulate the wallet (or admin Fernet ciphertext) "
                "with the new pair.", table, column, non_empty,
            )
        cr.execute(
            'ALTER TABLE "{table}" DROP COLUMN "{column}"'.format(
                table=table, column=column,
            )
        )
        _logger.info(
            "Dropped column %s.%s as part of 18.0.5.0.0 security migration.",
            table, column,
        )
