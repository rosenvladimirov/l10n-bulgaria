#  Part of Odoo. See LICENSE file for full copyright and licensing details.


def migrate(cr, version):
    """Мигрира данните от старите полета"""
    if not version:
        return

    # l10n_bg_name → l10n_bg_document_number
    cr.execute("""
        UPDATE account_move
        SET l10n_bg_document_number = l10n_bg_name
        WHERE l10n_bg_name IS NOT NULL
          AND (l10n_bg_document_number IS NULL OR l10n_bg_document_number = '');
    """)
