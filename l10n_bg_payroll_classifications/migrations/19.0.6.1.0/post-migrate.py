"""Post-migration hook for 19.0.6.1.0 — DEF-12 MOD noupdate refactor.

The MOD values used to live as columns in the CSV-based seed; from
this version they are kept in a separate XML data file flagged
noupdate=1 so user-edited MOD amounts (EUR for 2026 onwards) survive
upgrades.

Existing databases that already have MOD values populated do NOT need
any action — the columns are simply removed from the CSV import, so
nothing overwrites the existing rows. This hook only runs a sanity log.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        "SELECT COUNT(*) FROM bg_hr_payroll_economic_activity "
        "WHERE COALESCE(mod_manager, 0) + COALESCE(mod_specialist, 0) + "
        "      COALESCE(mod_technician, 0) + COALESCE(mod_clerk, 0) + "
        "      COALESCE(mod_service, 0) + COALESCE(mod_skilled, 0) + "
        "      COALESCE(mod_operator, 0) + COALESCE(mod_elementary, 0) > 0"
    )
    populated = cr.fetchone()[0]
    _logger.info(
        "DEF-12 migration: %d bg.hr.payroll.economic.activity rows "
        "carry non-zero MOD values; they are preserved under the new "
        "noupdate=1 layout.",
        populated,
    )
