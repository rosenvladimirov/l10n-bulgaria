# -*- coding: utf-8 -*-
# v19 Boolean капан (QA на Пламена, 2026-06-10): requires_allocation в Odoo 19
# е Boolean (в 18 беше Selection 'yes'/'no'); XML стойността "no" се парсва
# като truthy → новите кодове 18/19 се създадоха с requires_allocation=True и
# блокираха заявки без allocation. Data файлът е оправен (eval="False"), но
# записите са noupdate=1 → force-write за съществуващи бази.

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

NO_ALLOCATION = ['holiday_status_nssi_18', 'holiday_status_nssi_19']


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for name in NO_ALLOCATION:
        rec = env.ref('l10n_bg_hr_holidays.%s' % name, raise_if_not_found=False)
        if rec and rec.requires_allocation:
            rec.requires_allocation = False
            _logger.info("requires_allocation=False форсиран на %s", name)
