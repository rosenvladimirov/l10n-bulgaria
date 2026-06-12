# -*- coding: utf-8 -*-
# DEF-27 (QA рунд 2 на Пламена, 2026-06-11):
# 1. Код 17 „Mental Health Leave" не съществува в П9 класификацията на НОИ →
#    архивира се (active=False); записът е махнат от data XML за нови бази.
# 2. Generic довършване на v19 Boolean капана (requires_allocation): ВСИЧКИ
#    типове на модула освен петте allocation-базирани трябва да са False —
#    fresh-създадените на v19 със стринга "no" са станали True (хвана се на
#    18/19, после и на KT157-3/кончина; тук затваряме всички наведнъж).
#    Директен SQL: core write() гард забранява смяната при взети отпуски;
#    True→False е безопасната посока.
# 20/master: hr.leave.type е слят в hr.work.entry.type → таблица
# hr_work_entry_type + ir_model_data model='hr.work.entry.type'.

import logging

_logger = logging.getLogger(__name__)

# единствените allocation-базирани типове (eval="True" в data XML)
ALLOCATION_TYPES = (
    'holiday_status_kt_annual',
    'holiday_status_kt_hazardous',
    'holiday_status_kt_irregular',
    'holiday_status_kt_disabled',
    'holiday_status_kt_education_annual',
)


def migrate(cr, version):
    # 1. архив на код 17
    cr.execute("""
        UPDATE hr_work_entry_type t SET active = FALSE
        FROM ir_model_data d
        WHERE d.model = 'hr.work.entry.type' AND d.res_id = t.id
          AND d.module = 'l10n_bg_hr_holidays'
          AND d.name = 'holiday_status_nssi_17'
          AND t.active = TRUE
    """)
    _logger.info("Код 17 архивиран: %s запис(а)", cr.rowcount)

    # 2. requires_allocation=False за всички не-allocation типове на модула
    cr.execute("""
        UPDATE hr_work_entry_type t SET requires_allocation = FALSE
        FROM ir_model_data d
        WHERE d.model = 'hr.work.entry.type' AND d.res_id = t.id
          AND d.module = 'l10n_bg_hr_holidays'
          AND d.name NOT IN %s
          AND t.requires_allocation = TRUE
    """, (ALLOCATION_TYPES,))
    _logger.info("requires_allocation=False форсиран на %s типа", cr.rowcount)
