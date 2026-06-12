# -*- coding: utf-8 -*-
# DEF-27 (QA рунд 2 на Пламена, 2026-06-11):
# Код 17 „Mental Health Leave" не съществува в П9 класификацията на НОИ →
# архивира се (active=False); записът е махнат от data XML за нови бази.
# 18 БЕЛЕЖКА: generic requires_allocation SQL частта от 19-ската миграция
# (19.0.1.10.3 т.2) НЕ е портната — на 18 requires_allocation е Selection
# ('yes'/'no') и Boolean капанът не съществува.

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE hr_leave_type t SET active = FALSE
        FROM ir_model_data d
        WHERE d.model = 'hr.leave.type' AND d.res_id = t.id
          AND d.module = 'l10n_bg_hr_holidays'
          AND d.name = 'holiday_status_nssi_17'
          AND t.active = TRUE
    """)
    _logger.info("Код 17 архивиран: %s запис(а)", cr.rowcount)
