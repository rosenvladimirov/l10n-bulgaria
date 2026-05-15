# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Upgrade 6.0.2 → 6.0.3 — премахни двата deprecated InfoPay
method records (``l10n_bg_infopay_domestic_bgn`` +
``l10n_bg_infopay_budget_bgn``).

След 01.01.2026 (BG в еврозоната) Borica маркира трите `-bgn`
endpoint-а като ``deprecated: true`` в integration_openapi.yaml.
Само ``l10n_bg_infopay_sepa_eur`` остава активен.

Pre-migration на bridge модулите (l10n_bg_infopay_oca_payment ≥1.3.3
и l10n_bg_infopay_ee_payment ≥1.3.3) трябва да тече ПРЕДИ този
скрипт за да изпразнят payment.mode / method.line / payment-line
references.  Ако bridge упгрейдът не е стартиран още, скриптът ще
fail-не с FK violation — operator-ът трябва да upgrade-не bridge
модулите едновременно с този."""

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
    method_ids = [row[0] for row in cr.fetchall()]
    if not method_ids:
        _logger.info(
            "InfoPay 6.0.3 pre-migration: deprecated methods already absent.",
        )
        return

    # Изтрий ir.model.data сочеща към deprecated method records.
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE model = 'account.payment.method'
          AND module || '.' || name IN %s
        """,
        (DEPRECATED_XMLIDS,),
    )
    _logger.info(
        "InfoPay 6.0.3 pre-migration: removed %d ir.model.data rows.",
        cr.rowcount,
    )

    # Изтрий самите method records.
    cr.execute(
        "DELETE FROM account_payment_method WHERE id IN %s",
        (tuple(method_ids),),
    )
    _logger.info(
        "InfoPay 6.0.3 pre-migration: deleted %d deprecated methods.",
        cr.rowcount,
    )
