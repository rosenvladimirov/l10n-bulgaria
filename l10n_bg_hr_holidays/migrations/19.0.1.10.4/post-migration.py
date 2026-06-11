# -*- coding: utf-8 -*-
# FEAT-6 опция А (потвърдена от ТРЗ 2026-06-11, тест кейс Милена Велчева):
# старите open-ended allocations (вкл. отвъд 2-год. давност по чл. 176а)
# получават date_to = 31.12 на max(година + давност, ТЕКУЩАТА година) —
# валидни са (не изгарят) и core sort-ът по date_to ги консумира ПЪРВИ.
# Предишната миграция (19.0.1.9.0) ги пропускаше с future-guard → Odoo ги
# нареждаше ПОСЛЕДНИ и новата квота се ядеше първа (потвърденият бъг).
# Идемпотентно: само date_to IS NULL, не пипа ръчно зададени дати.

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE hr_leave_allocation a
        SET date_to = make_date(
            GREATEST(
                EXTRACT(YEAR FROM a.date_from)::int
                    + t.l10n_bg_carryover_lapse_years,
                EXTRACT(YEAR FROM CURRENT_DATE)::int
            ), 12, 31)
        FROM hr_leave_type t
        WHERE t.id = a.holiday_status_id
          AND COALESCE(t.l10n_bg_carryover_lapse_years, 0) > 0
          AND a.date_to IS NULL
          AND a.date_from IS NOT NULL
          AND a.accrual_plan_id IS NULL
          AND a.active = TRUE
          AND a.state != 'refuse'
    """)
    _logger.info("FEAT-6/A: date_to backfill на %s allocations", cr.rowcount)
