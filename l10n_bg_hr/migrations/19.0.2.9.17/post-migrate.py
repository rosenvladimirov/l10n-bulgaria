# -*- coding: utf-8 -*-
# DEF-210 т. 1 (Пламена, 15.10.2026): отметките „какво се променя“ за
# заварените ДС. Видът дава своята отметка; „Друго“ — отметки по попълнените
# нови стойности (там формата показваше всички страници наведнъж). Внесените
# ДС без нито една стойност остават без отметки → ЕТЗ не се предлага (вече са
# подадени от досегашния софтуер). Командироването получава основание по
# чл. 121а, ал. 1, т. 1.
import logging

_logger = logging.getLogger(__name__)

FROM_TYPE = {
    'wage_change': 'l10n_bg_chg_wage',
    'position_change': 'l10n_bg_chg_position',
    'working_time_change': 'l10n_bg_chg_working_time',
    'leave_change': 'l10n_bg_chg_leave',
    'workplace_change': 'l10n_bg_chg_workplace',
    'contract_extension': 'l10n_bg_chg_term',
}

FROM_VALUES = {
    'l10n_bg_chg_wage': "coalesce(new_wage, 0) > 0",
    'l10n_bg_chg_position': "(new_job_id IS NOT NULL OR new_position_id IS NOT NULL)",
    'l10n_bg_chg_working_time': "(new_working_time_type IS NOT NULL OR new_resource_calendar_id IS NOT NULL)",
    'l10n_bg_chg_leave': "coalesce(new_leave_days, 0) > 0",
    'l10n_bg_chg_workplace': "(new_work_location_id IS NOT NULL OR coalesce(new_work_location, '') <> '')",
}


def migrate(cr, version):
    if not version:
        return
    total = 0
    for tip, flag in FROM_TYPE.items():
        cr.execute(
            f"UPDATE l10n_bg_hr_version_amendment SET {flag} = TRUE "
            "WHERE amendment_type = %s AND NOT coalesce(" + flag + ", FALSE)",
            (tip,))
        total += cr.rowcount
    for flag, condition in FROM_VALUES.items():
        cr.execute(
            f"UPDATE l10n_bg_hr_version_amendment SET {flag} = TRUE "
            f"WHERE amendment_type = 'other' AND {condition} "
            f"AND NOT coalesce({flag}, FALSE)")
        total += cr.rowcount
    cr.execute(
        "UPDATE l10n_bg_hr_version_amendment SET l10n_bg_legal_basis = "
        "CASE WHEN amendment_type = 'temporary_assignment' THEN 'art121a' "
        "ELSE 'art119' END WHERE l10n_bg_legal_basis IS NULL")
    _logger.info("DEF-210: %s отметки на заварени ДС, основание на %s ДС",
                 total, cr.rowcount)
