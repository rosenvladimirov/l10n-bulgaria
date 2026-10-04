import logging

_logger = logging.getLogger(__name__)

# „Случаен клиент“ вече е в l10n_bg_config (ADR l10n-bg-sales-report-119/0001).
# Ако config още не е взел идентификатора, той се прехвърля тук — иначе
# надграждането на този модул би изтрило партньора като осиротял запис.


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE ir_model_data SET module = 'l10n_bg_config'
        WHERE module = 'l10n_bg_pos_sales_report' AND name = 'partner_random_customer'
          AND NOT EXISTS (
              SELECT 1 FROM ir_model_data
              WHERE module = 'l10n_bg_config' AND name = 'partner_random_customer'
          )
        """
    )
    if cr.rowcount:
        _logger.info("Random customer moved to l10n_bg_config")
