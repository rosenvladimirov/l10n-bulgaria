import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration script to update document numbers"""
    _logger.info("Starting pre-migration for l10n_bg_config 18.0.8.0.1")

    # Проверяваме дали колоната l10n_bg_document_number съществува
    cr.execute("""
               SELECT column_name
               FROM information_schema.columns
               WHERE table_name = 'account_move'
                 AND column_name = 'l10n_bg_document_number'
               """)

    if cr.fetchone():
        _logger.info("Column l10n_bg_document_number exists, updating values")
        cr.execute("""
                   UPDATE account_move
                   SET l10n_bg_document_number = l10n_bg_name
                   WHERE l10n_bg_name IS NOT NULL
                     AND (l10n_bg_document_number IS NULL OR l10n_bg_document_number = '');
                   """)
        _logger.info(f"Updated {cr.rowcount} records")
    else:
        _logger.info("Column l10n_bg_document_number does not exist yet, skipping migration")
