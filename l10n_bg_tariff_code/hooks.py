import logging

_logger = logging.getLogger(__name__)


def pre_init_hook(env):
    """
    Маркира всички съществуващи account.move.line записи като ръчно въведени,
    за да се избегне автоматично преизчисляване на тарифите при инсталация.
    """
    _logger.info("Running pre_init_hook: Marking existing tariff rates as manual")

    # Първо добавяме колоната ако не съществува
    env.cr.execute("""
               SELECT column_name
               FROM information_schema.columns
               WHERE table_name = 'account_move_line'
                 AND column_name = 'l10n_bg_tariff_rate_is_manual'
                   """)

    if not env.cr.fetchone():
        _logger.info("Adding column l10n_bg_tariff_rate_is_manual")
        env.cr.execute("""
                   ALTER TABLE account_move_line
                       ADD COLUMN l10n_bg_tariff_rate_is_manual BOOLEAN DEFAULT FALSE
                   """)

    # Задаваме TRUE за всички съществуващи записи
    env.cr.execute("""
               UPDATE account_move_line
               SET l10n_bg_tariff_rate_is_manual = TRUE
               WHERE id IS NOT NULL
               """)

    affected_rows = env.cr.rowcount
    _logger.info(f"Marked {affected_rows} existing account.move.line records as manual")
