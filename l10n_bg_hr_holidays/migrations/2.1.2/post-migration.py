# -*- coding: utf-8 -*-
# v19 Boolean капан (QA на Пламена, 2026-06-10): requires_allocation в Odoo 19+
# е Boolean (в 18 беше Selection 'yes'/'no'); XML стойността "no" се парсва
# като truthy → новите кодове 18/19 се създадоха с requires_allocation=True и
# блокираха заявки без allocation. Data файлът е оправен (eval="False"), но
# записите са noupdate=1 → force за съществуващи бази.
#
# Директен SQL (не ORM): core write() забранява смяна на requires_allocation
# при съществуващи отпуски от типа (QA вече е създала такива). Посоката
# True→False е безопасна — отпуските стават безалокационни, нищо не губи
# валидност; затова guard-ът се заобикаля съзнателно.
#
# 20/master: hr.leave.type е слят в hr.work.entry.type → таблица
# hr_work_entry_type + ir_model_data model='hr.work.entry.type'.

import logging

_logger = logging.getLogger(__name__)

NO_ALLOCATION = ('holiday_status_nssi_18', 'holiday_status_nssi_19')


def migrate(cr, version):
    cr.execute("""
        UPDATE hr_work_entry_type t
        SET requires_allocation = FALSE
        FROM ir_model_data d
        WHERE d.model = 'hr.work.entry.type' AND d.res_id = t.id
          AND d.module = 'l10n_bg_hr_holidays' AND d.name IN %s
          AND t.requires_allocation = TRUE
    """, (NO_ALLOCATION,))
    _logger.info("requires_allocation=False форсиран на %s записа", cr.rowcount)
