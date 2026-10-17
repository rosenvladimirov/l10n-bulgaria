# -*- coding: utf-8 -*-
# Пламена, 17.10.2026 (ТГ 172654): видовете 014 и 016 носеха грешен български
# текст („стажуване по чл. 230“, „чиракуване по чл. 233б“). Деплоят е без
# --i18n-overwrite, затова се маха само българският текст на тези два записа;
# Odoo го зарежда наново от .po веднага след post-migrate.
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE hr_contract_type t
           SET name = t.name - 'bg_BG' - 'bg'
          FROM ir_model_data d
         WHERE d.model = 'hr.contract.type' AND d.res_id = t.id
           AND d.module = 'l10n_bg_hr' AND d.name IN ('l10n_bg_014', 'l10n_bg_016')
    """)
    _logger.info("Видове договори 014/016: преводи за презареждане: %s", cr.rowcount)
