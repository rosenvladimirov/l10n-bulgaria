# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE ir_model_data AS d
           SET module = 'l10n_bg_tax_offices',
               noupdate = FALSE
         WHERE d.module = 'l10n_bg'
           AND d.model = 'res.partner'
           AND d.name LIKE 'nra%%'
           AND NOT EXISTS (
               SELECT 1 FROM ir_model_data d2
                WHERE d2.module = 'l10n_bg_tax_offices'
                  AND d2.name = d.name
           )
        """
    )
    moved = cr.rowcount
    if moved:
        _logger.info(
            "l10n_bg_tax_offices: reclaimed %s nra%% ir.model.data records "
            "from l10n_bg module (pre-migration to %s)",
            moved,
            version,
        )
