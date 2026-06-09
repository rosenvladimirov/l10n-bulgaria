# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Post-migrate за FEAT-6 — FIFO консумация на годишния отпуск (КТ чл.176а §2).

Две стъпки:

1. Задава `l10n_bg_carryover_lapse_years = 2` на основния/допълнителния платен
   годишен отпуск (KT155 / KT156*). Records-ите са `noupdate="1"` → стойността
   от data XML се пропуска на съществуващи бази (sticky-noupdate), затова я
   пишем директно през ORM (същият похват като legal_caps миграцията).

2. Backfill на `date_to` на СЪЩЕСТВУВАЩИ open-ended allocations от тези типове,
   за да заработи core-ският date_to-sort като FIFO.

   ⚠️ CONSERVATIVE GUARD: задаваме date_to само когато изчислената дата е В
   БЪДЕЩЕТО (>= днес). Така поправяме реда за още валидния пренесен отпуск
   (докладвания бъг), но НЕ погасяваме ретроактивно отпуск, който вече е
   извън давност (computed date_to в миналото) — тези записи се оставят за
   ръчен/правен преглед, за да не се трият дни без надзор.
"""
import logging
from datetime import date

_logger = logging.getLogger(__name__)

# xml_id-та на carryover типовете и броя години давност (КТ чл.176а §2).
CARRYOVER_TYPES = [
    ("holiday_status_kt_annual", 2),     # KT155 — основен платен годишен
    ("holiday_status_kt_hazardous", 2),  # KT156A — вредни условия
    ("holiday_status_kt_irregular", 2),  # KT156B — ненормиран ден
    ("holiday_status_kt_disabled", 2),   # KT156C — намалена работоспособност
]


def migrate(cr, version):  # noqa: U100
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    # --- 1) флаг на leave type-овете (bypass noupdate) ---
    type_ids = []
    for xmlid, years in CARRYOVER_TYPES:
        rec = env.ref(
            f"l10n_bg_hr_holidays.{xmlid}", raise_if_not_found=False)
        if not rec:
            _logger.info("Carry-over flag skipped — xml_id missing: %s", xmlid)
            continue
        rec.l10n_bg_carryover_lapse_years = years
        type_ids.append(rec.id)

    if not type_ids:
        _logger.info("FEAT-6: no carry-over leave types found — nothing to do")
        return

    # --- 2) backfill date_to на open-ended allocations (future-guarded) ---
    today = date.today()
    allocations = env["hr.leave.allocation"].with_context(
        active_test=False).search([
            ("work_entry_type_id", "in", type_ids),
            ("date_to", "=", False),
            ("date_from", "!=", False),
            ("accrual_plan_id", "=", False),
        ])
    applied = 0
    skipped_past = 0
    for alloc in allocations:
        years = alloc.work_entry_type_id.l10n_bg_carryover_lapse_years
        computed = date(alloc.date_from.year + years, 12, 31)
        if computed < today:
            # Вече извън давност — не пипаме (ръчен преглед).
            skipped_past += 1
            continue
        alloc.date_to = computed
        applied += 1
    _logger.info(
        "FEAT-6: carry-over date_to set on %d allocations "
        "(%d left untouched — computed lapse already in the past)",
        applied, skipped_past)
