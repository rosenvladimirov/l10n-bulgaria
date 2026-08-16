# -*- coding: utf-8 -*-
# Force-apply на реасайна на doo_treatment по платец за неплатения отпуск
# (ЗЗО чл. 40, ал. 1, т. 1, б. „б", ТРЗ 2026-06-24).
#
# Капан (същият като в 19.0.1.10.1): всички hr.leave.type xml_id-та са създадени
# от hr_holidays_data.xml (noupdate=1) → ir.model.data.noupdate=t. При -u Odoo
# прескача update-ите от noupdate=0 файла hr_holidays_doo_treatment.xml щом
# ФЛАГЪТ на записа е true — затова noupdate=0 override-ът НЕ влиза на съществуващи
# бази (само при първоначален install). Форсираме през ORM.
#
# kt_unpaid: unpaid_no_doo → unpaid_employee (КТ чл. 160, по желание → лицето).
# professional_unpaid → unpaid_employer (чл. 158/161); childcare_8y →
# unpaid_employer (чл. 167а); production_necessity → unpaid_split (произв.
# необходимост / престой). Тези 4 захранват ЗО compute-а в l10n_bg_hr_payroll.

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
            _logger.warning("Leave type %s липсва — прескачам", name)
            continue
        rec.l10n_bg_doo_treatment = treatment
        n += 1
    _logger.info("doo_treatment реасайн по платец force-приложен на %s типа", n)
