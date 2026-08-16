# Part of Odoo. See LICENSE file for full copyright and licensing details.
# DEF-40: заковаване на работодателските дни (N) per болничен тип + включване
# на официалните празници в продължителността на болничните.
#
# Seed файлът hr_holidays_data.xml е noupdate="1" → промените по стойностите НЕ
# се преприлагат на съществуващи бази при -u. Затова force-write тук (директен
# SQL — заобикаля и core constraint-а _check_overlapping_public_holidays, който
# иначе би хвърлил ValidationError при налични отпуски върху празник).
#
# Каноничната таблица е потвърдена от ТРЗ (Пламена, 2026-06-17):
#   N=2: 03, 06, 09, 10, 12, 16, 18
#   N=0: 01, 02, 04, 05, 07, 08, 11, 13, 14, 15, 19
# 01/02/13 (трудова злополука/проф. болест) и 04/05/15 (майчинство) и без това
# се рутират по l10n_bg_doo_treatment настрани от работодателския split — N там
# е нулиран за чистота.

EMPLOYER_DAYS = {
    '01': 0, '02': 0, '03': 2, '04': 0, '05': 0, '06': 2, '07': 0,
    '08': 0, '09': 2, '10': 2, '11': 0, '12': 2, '13': 0, '14': 0,
    '15': 0, '16': 2, '18': 2, '19': 0,
}


def migrate(cr, version):
    # N per болничен код
    for code, n in EMPLOYER_DAYS.items():
        cr.execute(
            "UPDATE hr_leave_type SET l10n_bg_paid_days_unpaid_leave = %s "
            "WHERE l10n_bg_code = %s",
            (n, code),
        )
    # Болничните включват официалните празници в периода (поемат се от НОИ като
    # календарни дни) → „Игнориране на официални празници" = Да.
    cr.execute(
        "UPDATE hr_leave_type SET include_public_holidays_in_duration = TRUE "
        "WHERE l10n_bg_code IN %s",
        (tuple(EMPLOYER_DAYS.keys()),),
    )
