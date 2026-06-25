# -*- coding: utf-8 -*-
# Force-apply на реасайна на doo_treatment по платец за неплатения отпуск
# (ЗЗО чл. 40, ал. 1, т. 1, б. „б", ТРЗ 2026-06-24) — lockstep от 19.0 (afb5f66).
#
# Капан: hr.work.entry.type xml_id-тата са създадени от hr_holidays_data.xml
# (noupdate=1) → ir.model.data.noupdate=t. При -u Odoo прескача update-ите от
# noupdate=0 hr_holidays_doo_treatment.xml щом ФЛАГЪТ е true (само install).
# Затова форсираме през ORM. (master/20.0: типът отсъствие Е hr.work.entry.type.)
#
# ⚠️ Папката е БЕЗ serie префикс (`2.1.7`, не `19.4.2.1.7`) — иначе „Invalid
# version" и миграцията тихо НЕ се пуска.

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

DOO_TREATMENTS = {
    'holiday_status_kt_unpaid': 'unpaid_employee',
    'holiday_status_kt_professional_unpaid': 'unpaid_employer',
    'holiday_status_kt_childcare_8y': 'unpaid_employer',
    'holiday_status_kt_production_necessity': 'unpaid_split',
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    n = 0
    for name, treatment in DOO_TREATMENTS.items():
        rec = env.ref('l10n_bg_hr_holidays.%s' % name, raise_if_not_found=False)
        if not rec:
            _logger.warning("Work entry type %s липсва — прескачам", name)
            continue
        rec.l10n_bg_doo_treatment = treatment
        n += 1
    _logger.info("doo_treatment реасайн по платец force-приложен на %s типа", n)
