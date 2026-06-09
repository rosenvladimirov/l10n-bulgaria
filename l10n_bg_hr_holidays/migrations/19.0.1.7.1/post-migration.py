# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Post-migrate: apply Bulgarian legal caps to existing hr.work.entry.type records.

Background:
Original hr_holidays_data.xml seeds leave types with `noupdate="1"`. The
records' ir.model.data flag is thus `noupdate=True`, which causes Odoo to
SKIP subsequent updates from data files — even from `noupdate="0"` ones.
This is the "sticky noupdate" canonical Odoo behaviour.

For new field rollouts (like the legal caps in 18.0.1.7.0) that need to
land on existing DBs, the canonical solution is a post-migrate that writes
directly through the ORM, bypassing the ir.model.data noupdate gate.

The same values are also kept in `data/hr_holidays_legal_caps.xml` so
fresh installs apply them automatically.
"""
import logging

_logger = logging.getLogger(__name__)


# (xml_id, max_per_year, max_total, legal_reference)
LEGAL_CAPS = [
    # NSSI codes — медицински
    ("holiday_status_nssi_04", 0, 410, "КСО чл. 50, ал. 1; КТ чл. 163"),
    ("holiday_status_nssi_07", 10, 0, "КСО чл. 45, ал. 1, т. 2"),
    # KT codes — Кодекс на труда
    ("holiday_status_kt_marriage", 0, 2, "КТ чл. 157, ал. 1, т. 1"),
    ("holiday_status_kt_blood_donation", 0, 2, "КТ чл. 157, ал. 1, т. 2"),
    ("holiday_status_kt_bereavement", 0, 2, "КТ чл. 157, ал. 1, т. 3"),
    ("holiday_status_kt_disaster_training", 5, 0, "КТ чл. 157, ал. 1, т. 7"),
    ("holiday_status_kt_unpaid", 30, 0, "КТ чл. 160, ал. 1 (за признат стаж)"),
    ("holiday_status_kt_professional_paid", 25, 0, "КТ чл. 161, ал. 1"),
    ("holiday_status_kt_maternity_410", 0, 410, "КТ чл. 163, ал. 1"),
    ("holiday_status_kt_paternity", 0, 15, "КТ чл. 163, ал. 10"),
    ("holiday_status_kt_parent_illness", 10, 0, "КТ чл. 167; КСО чл. 45, ал. 1, т. 2"),
    ("holiday_status_kt_childcare_8y", 44, 0, "КТ чл. 167а (2 месеца ≈ 44 раб. дни)"),
    ("holiday_status_kt_education_annual", 25, 0, "КТ чл. 169"),
    ("holiday_status_kt_final_exam", 0, 30, "КТ чл. 170"),
    ("holiday_status_kt_phd_research", 0, 132, "КТ чл. 171а (6 месеца ≈ 132 раб. дни)"),
    ("holiday_status_kt_phd_defense", 0, 22, "КТ чл. 171б (1 месец ≈ 22 раб. дни)"),
]


def migrate(cr, version):  # noqa: U100
    """Apply legal caps directly on existing hr.work.entry.type records."""
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    applied = 0
    skipped = 0
    for xmlid, max_year, max_total, ref in LEGAL_CAPS:
        rec = env.ref(
            f"l10n_bg_hr_holidays.{xmlid}", raise_if_not_found=False)
        if not rec:
            _logger.info("Legal cap skipped — xml_id missing: %s", xmlid)
            skipped += 1
            continue
        rec.write({
            "l10n_bg_max_days_per_year": max_year,
            "l10n_bg_max_days_total": max_total,
            "l10n_bg_legal_reference": ref,
        })
        applied += 1
    _logger.info(
        "Applied legal caps to %d leave types (%d skipped — missing xml_ids)",
        applied, skipped)
