# -*- coding: utf-8 -*-
# Преименуване на leave типове 05 и 07 (GAP-5 / GAP-2 от leave-types одита).
# Записите са в noupdate=1 секция → -u НЕ пипа name на съществуващи бази,
# затова форсираме през ORM (en_US + наличните bg езици).

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

RENAMES = {
    'l10n_bg_hr_holidays.holiday_status_nssi_05': {
        'en_US': 'Caring for Sick Child (under 2, on sick leave)',
        'bg': 'Гледане на болно дете до 2 г. (болничен лист)',
    },
    'l10n_bg_hr_holidays.holiday_status_nssi_07': {
        'en_US': 'Accompanying a Sick Family Member (Adult, 18+)',
        'bg': 'Придружаване на болен член на семейството (над 18 г.)',
    },
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    bg_langs = [
        code for code, _name in env['res.lang'].get_installed()
        if code.startswith('bg')
    ]
    for xmlid, names in RENAMES.items():
        rec = env.ref(xmlid, raise_if_not_found=False)
        if not rec:
            _logger.warning("Leave type %s не е намерен — прескачам", xmlid)
            continue
        rec.with_context(lang='en_US').name = names['en_US']
        for lang in bg_langs:
            rec.with_context(lang=lang).name = names['bg']
        _logger.info("Преименуван %s → %s", xmlid, names['en_US'])
