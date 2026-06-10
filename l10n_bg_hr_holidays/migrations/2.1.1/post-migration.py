# -*- coding: utf-8 -*-
# Force-apply на doo_treatment + legal caps (GAP-3 / GAP-2).
#
# Капан: всички hr.leave.type xml_id-та са създадени от hr_holidays_data.xml
# (noupdate=1) → ir.model.data.noupdate=t. При -u Odoo прескача update-ите
# от noupdate=0 файловете (hr_holidays_doo_treatment.xml,
# hr_holidays_legal_caps.xml) щом ФЛАГЪТ на записа е true — т.е. override
# файловете работят само при първоначален install. Затова форсираме през ORM
# (същият pattern като FEAT-2 register mapping force-write).

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

DOO_TREATMENTS = {
    # трудова злополука / профболест (КСО чл. 41 — 90%)
    'holiday_status_nssi_01': 'nssi_work_accident',
    'holiday_status_nssi_02': 'nssi_work_accident',
    'holiday_status_nssi_13': 'nssi_work_accident',
    # общо заболяване и приравнени (КСО чл. 40)
    'holiday_status_nssi_03': 'nssi_sick',
    'holiday_status_nssi_06': 'nssi_sick',
    'holiday_status_nssi_07': 'nssi_sick',
    'holiday_status_nssi_08': 'nssi_sick',
    'holiday_status_nssi_09': 'nssi_sick',
    'holiday_status_nssi_10': 'nssi_sick',
    'holiday_status_nssi_11': 'nssi_sick',
    'holiday_status_nssi_12': 'nssi_sick',
    'holiday_status_nssi_14': 'nssi_sick',
    'holiday_status_nssi_16': 'nssi_sick',
    'holiday_status_nssi_17': 'nssi_sick',
    'holiday_status_nssi_18': 'nssi_sick',
    'holiday_status_nssi_19': 'nssi_sick',
    # майчинство (КСО чл. 50/53)
    'holiday_status_nssi_04': 'nssi_maternity',
    'holiday_status_nssi_05': 'nssi_maternity',
    'holiday_status_nssi_15': 'nssi_maternity',
    'holiday_status_kt_maternity_410': 'nssi_maternity',
    'holiday_status_kt_paternity': 'nssi_maternity',
    'holiday_status_kt_childcare_2y': 'nssi_maternity',
    'holiday_status_kt_breastfeeding': 'nssi_maternity',
    # неплатен над 30 дни (КТ чл. 160; КСО чл. 9, ал. 2, т. 3)
    'holiday_status_kt_unpaid': 'unpaid_no_doo',
}

LEGAL_CAPS = {
    'holiday_status_nssi_19': {
        'l10n_bg_max_days_per_year': 60,
        'l10n_bg_legal_reference': 'КСО чл. 45, ал. 1, т. 1',
    },
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for name, treatment in DOO_TREATMENTS.items():
        rec = env.ref('l10n_bg_hr_holidays.%s' % name, raise_if_not_found=False)
        if not rec:
            _logger.warning("Leave type %s липсва — прескачам", name)
            continue
        rec.l10n_bg_doo_treatment = treatment
    for name, vals in LEGAL_CAPS.items():
        rec = env.ref('l10n_bg_hr_holidays.%s' % name, raise_if_not_found=False)
        if rec:
            rec.write(vals)
    _logger.info("doo_treatment force-приложен на %s типа + caps", len(DOO_TREATMENTS))
