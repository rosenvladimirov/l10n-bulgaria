"""Bulgaria 2026 — Payroll Classifications

Year-stamped МОД migration BGN → EUR + НКПД audit.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP

_logger = logging.getLogger(__name__)

YEAR = 2026
DATE_FROM_NEW = f"{YEAR}-01-01"
DATE_TO_OLD = f"{YEAR - 1}-12-31"
EUR_RATE = Decimal("1.95583")  # ЗВЕРБ фиксиран курс
EUR_CONVERSION_NEEDED = True   # 2026 е първата евро година; за 2027+ → False

MOD_FIELDS = (
    "mod_manager",
    "mod_specialist",
    "mod_technician",
    "mod_clerk",
    "mod_service",
    "mod_skilled",
    "mod_operator",
    "mod_elementary",
)

MODULE = "l10n_bg_2026_classifications"


def _to_eur(bgn_value):
    """Convert BGN → EUR per ЗВЕРБ rules: divide then round to 0.01."""
    if not bgn_value:
        return 0.0
    eur = Decimal(str(bgn_value)) / EUR_RATE
    return float(eur.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def post_init_hook(env):
    """Migrate МОД records from BGN to EUR for the new year.

    Behaviour:
      1. Find all `bg.hr.payroll.economic.activity` records that are
         currently active (date_to is False) and have date_from in the
         prior year or earlier;
      2. For each — close the old record (date_to = YEAR-1-12-31) and
         create a clone with date_from = YEAR-01-01 and all mod_*
         fields converted ÷ 1.95583 (rounded to 2 decimals);
      3. Skip if a record already exists with the new date_from for
         the same code (idempotent re-install);
      4. Audit НКПД (no changes for 2026 — log only).
    """
    Activity = env["bg.hr.payroll.economic.activity"]
    NCOP = env["bg.hr.payroll.ncop.classification"]

    # ----- 1. МОД миграция -----
    if EUR_CONVERSION_NEEDED:
        active_records = Activity.search([
            ("date_from", "<=", DATE_TO_OLD),
            ("date_to", "=", False),
            ("active", "=", True),
        ])
        _logger.info(
            "[%s] Found %d active МОД records to migrate BGN->EUR for %d",
            MODULE, len(active_records), YEAR,
        )

        migrated = skipped = 0
        for old_rec in active_records:
            # Idempotency: skip ако вече има record за нашата година + код
            existing = Activity.search([
                ("code", "=", old_rec.code),
                ("level", "=", old_rec.level),
                ("date_from", "=", DATE_FROM_NEW),
            ], limit=1)
            if existing:
                skipped += 1
                continue

            # Close old record
            old_rec.write({"date_to": DATE_TO_OLD})

            # Clone in EUR for new year
            new_vals = {
                "name": old_rec.name,
                "code": old_rec.code,
                "parent_id": old_rec.parent_id.id if old_rec.parent_id else False,
                "level": old_rec.level,
                "active": True,
                "date_from": DATE_FROM_NEW,
            }
            for field in MOD_FIELDS:
                bgn_value = getattr(old_rec, field, 0.0)
                new_vals[field] = _to_eur(bgn_value)

            Activity.create(new_vals)
            migrated += 1

        _logger.info(
            "[%s] МОД migration: %d new EUR records created, "
            "%d skipped (already existed). Old records closed at %s.",
            MODULE, migrated, skipped, DATE_TO_OLD,
        )
    else:
        _logger.info(
            "[%s] EUR_CONVERSION_NEEDED=False - skip МОД migration "
            "(values already in EUR)", MODULE,
        )

    # ----- 2. НКПД audit -----
    ncop_count = NCOP.search_count([])
    _logger.info(
        "[%s] НКПД-2011: %d records present. No structural changes "
        "for %d (last NSI revision was 2011).",
        MODULE, ncop_count, YEAR,
    )
