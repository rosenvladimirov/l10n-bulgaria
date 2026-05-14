"""Pre-migration for 18.0.16.0.0.

Rename of account.move.line.l10n_bg_account_tag_ids → account_tag_ids.

Without this hook Odoo would mark the old field for deletion (dropping
the M2M data) and create an empty new field. Renaming the ir.model.fields
record before the registry rebuilds preserves the data in
l10n_bg_aml_account_tag_rel (relation table name is unchanged).
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        UPDATE ir_model_fields
        SET name = 'account_tag_ids'
        WHERE model = 'account.move.line'
          AND name = 'l10n_bg_account_tag_ids'
          AND NOT EXISTS (
              SELECT 1 FROM ir_model_fields
              WHERE model = 'account.move.line'
                AND name = 'account_tag_ids'
          )
    """)
