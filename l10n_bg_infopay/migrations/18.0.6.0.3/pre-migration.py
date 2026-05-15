# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Upgrade 6.0.2 → 6.0.3 — премахни двата deprecated InfoPay
method records (``l10n_bg_infopay_domestic_bgn`` +
``l10n_bg_infopay_budget_bgn``) и всички references към тях.

След 01.01.2026 (BG в еврозоната) Borica маркира трите `-bgn`
endpoint-а като ``deprecated: true`` в integration_openapi.yaml.
Само ``l10n_bg_infopay_sepa_eur`` остава активен.

Тъй като `l10n_bg_infopay` е dep на bridge модулите, той upgrade-ва
ПЪРВИ.  Към момента, в който този script тече, bridge модулите още
не са пуснали техните pre-migrations — значи трябва **тук** да
изпразним всички references преди да изтрием самите method records:

  * account.payment.line — отвържи payment_mode_id
  * account.payment — отвържи payment_method_line_id
  * account.payment.method.line — DELETE
  * account.payment.mode — DELETE
  * account.payment.method — DELETE (накрая)
  * ir.model.data — DELETE свързаните XMLID-та

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
        "InfoPay 6.0.3 pre-migration: cleaning references за methods %s.",
        list(DEPRECATED_CODES),
    )

    # 1) account.payment.line — premakhni references KЪM modes.
    cr.execute(
        """
        UPDATE account_payment_line apl
        SET payment_mode_id = NULL
        FROM account_payment_mode apm
        WHERE apl.payment_mode_id = apm.id
          AND apm.payment_method_id IN %s
        """,
        (method_ids,),
    )
    _logger.info("  unset payment_mode_id on %d payment.lines", cr.rowcount)

    # 2) account.payment — premakhni references KЪM method.lines.
    cr.execute(
        """
        UPDATE account_payment
        SET payment_method_line_id = NULL
        WHERE payment_method_line_id IN (
            SELECT id FROM account_payment_method_line
            WHERE payment_method_id IN %s
        )
        """,
        (method_ids,),
    )
    _logger.info("  unset method_line_id on %d account.payments", cr.rowcount)

    # 3) account.payment.method.line.
    cr.execute(
        "DELETE FROM account_payment_method_line WHERE payment_method_id IN %s",
        (method_ids,),
    )
    _logger.info("  deleted %d method.lines", cr.rowcount)

    # 4) account.payment.mode.
    cr.execute(
        "DELETE FROM account_payment_mode WHERE payment_method_id IN %s",
        (method_ids,),
    )
    _logger.info("  deleted %d payment.modes", cr.rowcount)

    # 5) ir.model.data за XML IDs.
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE model = 'account.payment.method'
          AND module || '.' || name IN %s
        """,
        (DEPRECATED_XMLIDS,),
    )
    _logger.info("  removed %d ir.model.data rows", cr.rowcount)

    # 6) Самите method records.
    cr.execute(
        "DELETE FROM account_payment_method WHERE id IN %s",
        (method_ids,),
    )
    _logger.info("  deleted %d deprecated methods", cr.rowcount)
