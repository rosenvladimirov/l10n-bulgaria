import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """v18 -> v19 pre-migration for l10n_bg_config.

    The BG fields on account_move (l10n_bg_document_number, l10n_bg_name,
    l10n_bg_name_value) keep the same schema across v18 and v19, but
    l10n_bg_name became a `related` field to l10n_bg_document_number with
    l10n_bg_name_value as the underlying stored column. This script ensures
    legacy rows that only had l10n_bg_name populated still propagate to
    l10n_bg_name_value / l10n_bg_document_number before Odoo rebuilds the
    computed graph on upgrade.
    """
    if not version:
        return

    _logger.info("l10n_bg_config pre-migrate: start (from %s)", version)

    cr.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'account_move'
          AND column_name IN (
            'l10n_bg_document_number',
            'l10n_bg_name',
            'l10n_bg_name_value'
          )
        """
    )
    columns = {row[0] for row in cr.fetchall()}

    if 'l10n_bg_name_value' in columns and 'l10n_bg_name' in columns:
        cr.execute(
            """
            UPDATE account_move
            SET l10n_bg_name_value = l10n_bg_name
            WHERE l10n_bg_name IS NOT NULL
              AND l10n_bg_name <> ''
              AND (l10n_bg_name_value IS NULL OR l10n_bg_name_value = '')
            """
        )
        _logger.info("l10n_bg_name -> l10n_bg_name_value: %d rows", cr.rowcount)

    if 'l10n_bg_document_number' in columns and 'l10n_bg_name_value' in columns:
        cr.execute(
            """
            UPDATE account_move
            SET l10n_bg_document_number = l10n_bg_name_value
            WHERE l10n_bg_name_value IS NOT NULL
              AND l10n_bg_name_value <> ''
              AND (l10n_bg_document_number IS NULL OR l10n_bg_document_number = '')
            """
        )
        _logger.info(
            "l10n_bg_name_value -> l10n_bg_document_number: %d rows", cr.rowcount
        )

    _logger.info("l10n_bg_config pre-migrate: done")
