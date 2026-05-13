# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later.

"""Move admin (cron) InfoPay credentials from per-company Fernet
columns into the token owner's crypto wallet.

5.0.0 stored admin uniqueId/token as Fernet ciphertext on res.company
(symmetric key in ir.config_parameter).  6.0.0 stores them under
``infopay_admin_unique_id`` / ``infopay_admin_access_token`` keys in the
owner's wallet — same security boundary as the user-side pair.

Strategy:
 1. Read the Fernet key from ir.config_parameter.
 2. For every company whose Fernet ciphertext columns are populated and
    whose token owner is set, decrypt + write the pair into the owner's
    wallet.
 3. Drop the two Fernet columns.  Keep the Fernet ICP key only if at
    least one company was skipped (so an operator can recover manually).
"""

import logging

from cryptography.fernet import Fernet, InvalidToken

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

FERNET_PARAM = "l10n_bg_infopay.admin_fernet_key"
ADMIN_UID_KEY = "infopay_admin_unique_id"
ADMIN_TOK_KEY = "infopay_admin_access_token"


def migrate(cr, version):
    if not version:
        return

    # Columns may already be gone if someone replayed the migration —
    # bail out cleanly in that case.
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'res_company'
          AND column_name IN (
            'l10n_bg_infopay_admin_unique_id_encrypted',
            'l10n_bg_infopay_admin_token_encrypted'
          )
    """)
    present_cols = {row[0] for row in cr.fetchall()}
    if not present_cols:
        _logger.info(
            "InfoPay admin Fernet columns already dropped — skip migration.",
        )
        return

    cr.execute(
        "SELECT value FROM ir_config_parameter WHERE key = %s",
        (FERNET_PARAM,),
    )
    row = cr.fetchone()
    fernet_key = row[0] if row else None

    cr.execute("""
        SELECT id, name,
               l10n_bg_infopay_admin_unique_id_encrypted,
               l10n_bg_infopay_admin_token_encrypted,
               l10n_bg_infopay_token_user_id
        FROM res_company
        WHERE l10n_bg_infopay_admin_unique_id_encrypted IS NOT NULL
           OR l10n_bg_infopay_admin_token_encrypted IS NOT NULL
    """)
    rows = cr.fetchall()

    skipped = []
    migrated = []

    if rows:
        if not fernet_key:
            _logger.error(
                "InfoPay admin Fernet key missing but %s company(ies) "
                "still hold ciphertext — cannot migrate; dropping "
                "columns would lose data.  Aborting.", len(rows),
            )
            return
        f = Fernet(fernet_key.encode())
        env = api.Environment(cr, SUPERUSER_ID, {})
        Wallet = env["crypto.wallet"].sudo()
        Users = env["res.users"].sudo()

        for company_id, company_name, ct_uid, ct_tok, owner_id in rows:
            if not owner_id:
                _logger.warning(
                    "Company %s (id=%s): admin Fernet ciphertext present "
                    "but no token owner — skip (operator must re-set "
                    "via _l10n_bg_infopay_set_admin_credentials).",
                    company_name, company_id,
                )
                skipped.append(company_id)
                continue

            try:
                uid_plain = (
                    f.decrypt(ct_uid.encode()).decode() if ct_uid else None
                )
                tok_plain = (
                    f.decrypt(ct_tok.encode()).decode() if ct_tok else None
                )
            except InvalidToken:
                _logger.error(
                    "Company %s (id=%s): admin Fernet ciphertext cannot "
                    "be decrypted — Fernet key may have rotated.  Skip.",
                    company_name, company_id,
                )
                skipped.append(company_id)
                continue

            owner = Users.browse(owner_id)
            if not owner.exists():
                _logger.warning(
                    "Company %s (id=%s): token owner user %s no longer "
                    "exists — skip.", company_name, company_id, owner_id,
                )
                skipped.append(company_id)
                continue

            try:
                wallet = Wallet.get_user_wallet_or_create(user_id=owner.id)
                if uid_plain:
                    wallet.add_key_with_user_password(
                        ADMIN_UID_KEY, "api_key", uid_plain,
                    )
                if tok_plain:
                    wallet.add_key_with_user_password(
                        ADMIN_TOK_KEY, "api_key", tok_plain,
                    )
            except Exception as exc:  # noqa: BLE001
                _logger.error(
                    "Company %s (id=%s): wallet write failed — %s.  Skip.",
                    company_name, company_id, exc,
                )
                skipped.append(company_id)
                continue

            migrated.append(company_id)
            _logger.info(
                "Migrated InfoPay admin creds for company %s → wallet "
                "of %s.", company_name, owner.login,
            )

    # Drop the Fernet columns regardless of whether any company had
    # data — they're gone from the model declarations in 6.0.0.
    cr.execute("""
        ALTER TABLE res_company
        DROP COLUMN IF EXISTS l10n_bg_infopay_admin_unique_id_encrypted,
        DROP COLUMN IF EXISTS l10n_bg_infopay_admin_token_encrypted
    """)
    _logger.info("Dropped InfoPay admin Fernet columns from res_company.")

    if fernet_key and not skipped:
        cr.execute(
            "DELETE FROM ir_config_parameter WHERE key = %s",
            (FERNET_PARAM,),
        )
        _logger.info(
            "Dropped admin Fernet ICP key after successful migration "
            "(%s company/companies).", len(migrated),
        )
    elif skipped:
        _logger.warning(
            "InfoPay admin Fernet ICP key kept (%s skipped, %s migrated) "
            "— remove manually after operator re-sets the skipped "
            "companies' admin credentials.", len(skipped), len(migrated),
        )
