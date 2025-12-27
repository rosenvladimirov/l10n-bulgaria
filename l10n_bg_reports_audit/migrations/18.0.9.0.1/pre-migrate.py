
def migrate(cr, version):
    """Мигрира данните от старите полета към стандартните l10n_bg_ledger полета"""
    if not version:
        return

    # Проверка дали старите колони съществуват
    cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'account_move'
          AND column_name IN ('l10n_bg_doc_type', 'l10n_bg_delivery_type')
    """)
    existing_columns = [row[0] for row in cr.fetchall()]

    # Копиране на l10n_bg_doc_type → l10n_bg_document_type
    if 'l10n_bg_doc_type' in existing_columns:
        cr.execute("""
            UPDATE account_move
            SET l10n_bg_document_type = l10n_bg_doc_type
            WHERE l10n_bg_doc_type IS NOT NULL
              AND (l10n_bg_document_type IS NULL OR l10n_bg_document_type = '');
        """)

    # Копиране на l10n_bg_delivery_type → l10n_bg_exemption_reason
    if 'l10n_bg_delivery_type' in existing_columns:
        cr.execute("""
            UPDATE account_move
            SET l10n_bg_exemption_reason = l10n_bg_delivery_type
            WHERE l10n_bg_delivery_type IS NOT NULL
              AND (l10n_bg_exemption_reason IS NULL OR l10n_bg_exemption_reason = '');
        """)
