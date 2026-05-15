# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Upgrade 6.0.2 → 6.0.3 — премахни двата deprecated InfoPay
method records (``l10n_bg_infopay_domestic_bgn`` +
``l10n_bg_infopay_budget_bgn``) и всички references към тях.

След 01.01.2026 (BG в еврозоната) Borica маркира трите `-bgn`
endpoint-а като ``deprecated: true`` в integration_openapi.yaml.
Само ``l10n_bg_infopay_sepa_eur`` остава активен.

`l10n_bg_infopay` е dep на bridge модулите, така че upgrade-ва ПЪРВИ.
Към момента, в който този script тече, bridge модулите още не са
пуснали техните pre-migrations — затова **тук** изпразваме всички
references преди да изтрием самите method records.

References (от \d account_payment_method / mode / method_line):
  * account_payment.payment_method_id              → SET NULL
  * account_payment.payment_method_line_id         → SET NULL
  * account_payment_register.payment_method_line_id → SET NULL
  * account_move.preferred_payment_method_line_id  → SET NULL
  * account_move.payment_mode_id                   → SET NULL
  * account_move_line.payment_mode_id              → SET NULL
  * account_payment_order.payment_method_id        → SET NULL
  * account_payment_order.payment_mode_id          → SET NULL
  * purchase_order.payment_mode_id                 → SET NULL
  * sale_order.payment_mode_id                     → SET NULL
  * account_journal_account_payment_mode_rel       → DELETE rows
  * account_payment_mode_variable_journal_rel      → DELETE rows
  * account_payment_mode.refund_payment_mode_id    → SET NULL
  * account_payment_method_line + payment_mode     → DELETE
  * ir_model_data + account_payment_method         → DELETE

Скриптът е идемпотентен — повторен запуск не fail-ва."""

import logging

_logger = logging.getLogger(__name__)

DEPRECATED_CODES = (
    "l10n_bg_infopay_domestic_bgn",
    "l10n_bg_infopay_budget_bgn",
)
DEPRECATED_XMLIDS = (
    "l10n_bg_infopay.account_payment_method_infopay_domestic_bgn",
    "l10n_bg_infopay.account_payment_method_infopay_budget_bgn",
)


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        "SELECT id FROM account_payment_method WHERE code IN %s",
        (DEPRECATED_CODES,),
    )
    method_ids = tuple(row[0] for row in cr.fetchall())
    if not method_ids:
        _logger.info(
            "InfoPay 6.0.3 pre-migration: deprecated methods already absent.",
        )
        return

    _logger.info(
        "InfoPay 6.0.3 pre-migration: cleaning references за methods %s "
        "(ids=%s).",
        list(DEPRECATED_CODES), list(method_ids),
    )

    # Compute method.line ids and mode ids ranged by deprecated methods.
    cr.execute(
        "SELECT id FROM account_payment_method_line WHERE payment_method_id IN %s",
        (method_ids,),
    )
    method_line_ids = tuple(row[0] for row in cr.fetchall())
    cr.execute(
        "SELECT id FROM account_payment_mode WHERE payment_method_id IN %s",
        (method_ids,),
    )
    mode_ids = tuple(row[0] for row in cr.fetchall())

    _logger.info(
        "  affected: %d method.lines, %d modes",
        len(method_line_ids), len(mode_ids),
    )

    # ── method-line references → SET NULL ───────────────────────────
    if method_line_ids:
        for table, column in (
            ("account_payment",          "payment_method_line_id"),
            ("account_payment_register", "payment_method_line_id"),
            ("account_move",             "preferred_payment_method_line_id"),
        ):
            cr.execute(
                f"UPDATE {table} SET {column} = NULL WHERE {column} IN %s",
                (method_line_ids,),
            )
            if cr.rowcount:
                _logger.info("  %s.%s: cleared %d rows",
                             table, column, cr.rowcount)

    # ── mode references → SET NULL ──────────────────────────────────
    if mode_ids:
        for table, column in (
            ("account_move",          "payment_mode_id"),
            ("account_move_line",     "payment_mode_id"),
            ("account_payment_order", "payment_mode_id"),
            ("purchase_order",        "payment_mode_id"),
            ("sale_order",            "payment_mode_id"),
            ("account_payment_mode",  "refund_payment_mode_id"),
        ):
            cr.execute(
                f"UPDATE {table} SET {column} = NULL WHERE {column} IN %s",
                (mode_ids,),
            )
            if cr.rowcount:
                _logger.info("  %s.%s: cleared %d rows",
                             table, column, cr.rowcount)
        # M2M tables — изтрий редовете.
        for table, column in (
            ("account_journal_account_payment_mode_rel",   "account_payment_mode_id"),
            ("account_payment_mode_variable_journal_rel",  "payment_mode_id"),
        ):
            cr.execute(
                f"DELETE FROM {table} WHERE {column} IN %s",
                (mode_ids,),
            )
            if cr.rowcount:
                _logger.info("  %s: deleted %d M2M rows", table, cr.rowcount)

    # ── method references → SET NULL ────────────────────────────────
    for table, column in (
        ("account_payment",       "payment_method_id"),
        ("account_payment_order", "payment_method_id"),
    ):
        cr.execute(
            f"UPDATE {table} SET {column} = NULL WHERE {column} IN %s",
            (method_ids,),
        )
        if cr.rowcount:
            _logger.info("  %s.%s: cleared %d rows",
                         table, column, cr.rowcount)

    # ── DELETE child records ────────────────────────────────────────
    if method_line_ids:
        cr.execute(
            "DELETE FROM account_payment_method_line WHERE id IN %s",
            (method_line_ids,),
        )
        _logger.info("  deleted %d method.lines", cr.rowcount)
    if mode_ids:
        cr.execute(
            "DELETE FROM account_payment_mode WHERE id IN %s",
            (mode_ids,),
        )
        _logger.info("  deleted %d payment.modes", cr.rowcount)

    # ── ir.model.data ───────────────────────────────────────────────
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE model = 'account.payment.method'
          AND module || '.' || name IN %s
        """,
        (DEPRECATED_XMLIDS,),
    )
    _logger.info("  removed %d ir.model.data rows", cr.rowcount)

    # ── method records themselves ───────────────────────────────────
    cr.execute(
        "DELETE FROM account_payment_method WHERE id IN %s",
        (method_ids,),
    )
    _logger.info("  deleted %d deprecated methods", cr.rowcount)
