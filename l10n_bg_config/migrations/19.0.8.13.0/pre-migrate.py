import logging

_logger = logging.getLogger(__name__)

# „Случаен клиент“ (ЕИК 15 деветки) се мести от l10n_bg_pos_sales_report в
# l10n_bg_config (ADR l10n-bg-sales-report-119/0001). Преди config да зареди
# своя запис, външният идентификатор се прехвърля към config — иначе ще се
# създаде втори партньор. Ако партньорът съществува без идентификатор
# (създаден на ръка), той се закача към идентификатора на config.

NAME = "partner_random_customer"
UIC = "9" * 15


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "SELECT 1 FROM ir_model_data WHERE module = 'l10n_bg_config' AND name = %s",
        (NAME,),
    )
    if cr.fetchone():
        return
    cr.execute(
        """
        UPDATE ir_model_data SET module = 'l10n_bg_config'
        WHERE module = 'l10n_bg_pos_sales_report' AND name = %s
        RETURNING res_id
        """,
        (NAME,),
    )
    row = cr.fetchone()
    if row:
        _logger.info("Random customer %s moved to l10n_bg_config", row[0])
        return
    cr.execute(
        "SELECT id FROM res_partner WHERE l10n_bg_uic = %s ORDER BY id LIMIT 1",
        (UIC,),
    )
    row = cr.fetchone()
    if row:
        cr.execute(
            """
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            VALUES ('l10n_bg_config', %s, 'res.partner', %s, TRUE)
            """,
            (NAME, row[0]),
        )
        _logger.info("Existing random customer %s bound to l10n_bg_config", row[0])
