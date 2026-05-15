# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Upgrade 6.0.3 → 6.0.4 — преименувай method label
„InfoPay SEPA EUR“ → „InfoPay Credit Transfer (EUR)“.

`data/account_payment_method.xml` е ``noupdate="1"`` → при `-u`
Odoo НЕ пре-зарежда record-а, затова name-ът трябва да се update-не
тук.  ``name`` е jsonb translatable (Odoo 18) — пипаме само
``en_US`` ключа и само ако стойността е старата (за да не
override-нем ръчна корекция от оператора).

Идемпотентен."""

import logging

_logger = logging.getLogger(__name__)

OLD_NAME = "InfoPay SEPA EUR"
NEW_NAME = "InfoPay Credit Transfer (EUR)"


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        UPDATE account_payment_method
        SET name = jsonb_set(
            COALESCE(name, '{}'::jsonb), '{en_US}', to_jsonb(%s::text)
        )
        WHERE code = 'l10n_bg_infopay_sepa_eur'
          AND name->>'en_US' = %s
        """,
        (NEW_NAME, OLD_NAME),
    )
    _logger.info(
        "InfoPay 6.0.4 post-migration: renamed %d payment.method record(s) "
        "→ '%s'.", cr.rowcount, NEW_NAME,
    )
