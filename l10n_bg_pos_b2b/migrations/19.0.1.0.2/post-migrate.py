# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).


def migrate(cr, version):
    # 19.0.1.0.0 зареждаше всички B2B купувачи в касата; браузърът ги пази
    # в IndexedDB и ги слепва с новите данни при всяко отваряне — касата
    # остава бавна и след поправката. Нов last_data_change кара всеки
    # браузър да изчисти локалния кеш при следващото отваряне на касата.
    if not version:
        return
    cr.execute(
        "UPDATE pos_config SET last_data_change = now() at time zone 'UTC' "
        "WHERE l10n_bg_b2b_mode IS NOT NULL AND l10n_bg_b2b_mode != 'off'"
    )
