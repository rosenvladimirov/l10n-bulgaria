# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Upgrade 6.0.4 → 6.0.5 — върни ясното SEPA име.

В 6.0.4 преименувахме `l10n_bg_infopay_sepa_eur` на „InfoPay Credit
Transfer (EUR)“ (за да не звучи „само за чужбина“).  Сега имаме
ДВА отделни метода — SEPA (трансгранично) + Domestic (BG→BG) —
така че SEPA-методът пак носи „SEPA“ в името.

  • `l10n_bg_infopay_sepa_eur`     → „InfoPay SEPA (EUR)“  (rename тук)
  • `l10n_bg_infopay_domestic_eur` → „InfoPay Domestic (EUR)“

Domestic-методът е НОВ xmlid в data/account_payment_method.xml —
Odoo го създава автоматично при `-u` (noupdate=1 пази само
съществуващи records от override, нови records се зареждат).
Затова тук пипаме само rename-а на sepa_eur.

``name`` е jsonb translatable (Odoo 18); пипаме само ``en_US``
ключа и само ако е генеричната 6.0.4 стойност (запазваме ръчни
корекции).  Идемпотентен."""

import logging

_logger = logging.getLogger(__name__)

OLD_NAME = "InfoPay Credit Transfer (EUR)"
NEW_NAME = "InfoPay SEPA (EUR)"


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
        "InfoPay 6.0.5 post-migration: renamed %d sepa_eur method(s) "
        "→ '%s'.", cr.rowcount, NEW_NAME,
    )
