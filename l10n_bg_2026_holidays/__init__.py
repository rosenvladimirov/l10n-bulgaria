"""Bulgaria 2026 — Public Holidays

Idempotent year-stamped data module. The ``post_init_hook`` audits the
14 ``resource.calendar.leaves`` records loaded from this module's XML,
logging any drift without modifying prior-year holidays.
"""
import logging

_logger = logging.getLogger(__name__)

YEAR = 2026
MODULE = "l10n_bg_2026_holidays"

# 14 holiday XML record IDs for the year (без module prefix).
EXPECTED_HOLIDAYS = [
    "bg_holiday_2026_new_year",
    "bg_holiday_2026_liberation_day",
    "bg_holiday_2026_good_friday",
    "bg_holiday_2026_holy_saturday",
    "bg_holiday_2026_easter_sunday",
    "bg_holiday_2026_easter_monday",
    "bg_holiday_2026_labour_day",
    "bg_holiday_2026_st_george",
    "bg_holiday_2026_education_culture",
    "bg_holiday_2026_unification_day",
    "bg_holiday_2026_independence_day",
    "bg_holiday_2026_christmas_eve",
    "bg_holiday_2026_christmas_day",
    "bg_holiday_2026_christmas_2nd_day",
]


def post_init_hook(env):
    """Audit YYYY public holidays; never touch prior-year records.

    Behaviour:
      1. For each expected holiday XML record ID — resolve via env.ref;
      2. If missing → warning (XML data load issue);
      3. If date_from year != YEAR → notice (manual edit), leave as-is;
      4. Records for other years (different ``date_from`` year) are
         neither read nor modified.
    """
    verified = drift = missing = 0

    for xmlid_name in EXPECTED_HOLIDAYS:
        full_xmlid = f"{MODULE}.{xmlid_name}"
        rec = env.ref(full_xmlid, raise_if_not_found=False)
        if not rec:
            missing += 1
            _logger.warning(
                "[%s] missing holiday record %s — did data XML load?",
                MODULE, xmlid_name,
            )
            continue

        if rec.date_from and rec.date_from.year not in (YEAR - 1, YEAR):
            # date_from може да бъде 22:00 UTC of YYYY-01-01-1 за празник
            # на 1 jan, затова допускаме YEAR-1 също.
            drift += 1
            _logger.notice(
                "[%s] %s has date_from year=%s (expected %d or %d) — "
                "manual edit, leaving as-is.",
                MODULE, xmlid_name, rec.date_from.year, YEAR - 1, YEAR,
            )
            continue

        verified += 1

    _logger.info(
        "[%s] post_init_hook: %d verified, %d drift, %d missing. "
        "Other-year holidays untouched.",
        MODULE, verified, drift, missing,
    )
