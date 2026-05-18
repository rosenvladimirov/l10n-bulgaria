# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import logging

_logger = logging.getLogger(__name__)

# КИД секцията, която този индустриален пакет активира.
SECTOR_XMLID = "l10n_bg_config.kid_2025_C"


def post_init_hook(env):
    """Активира КИД сектор 'C' за всяка BG фирма и презарежда сметкоплана.

    Добавя секцията към ``res.company.l10n_bg_kid_ids`` (идемпотентно),
    след което презарежда chart template-а (същият проверен модел като
    другите ``l10n_bg_config_plugins_*`` data плъгове), за да пропусне
    install-филтърът сектор-специфичните сметки на този сектор. Нивото на
    свободния текст (``l10n_bg_kid_codes``) не се пипа — той е само
    bootstrap; M2M е авторитатен щом е попълнен.
    """
    section = env.ref(SECTOR_XMLID, raise_if_not_found=False)
    if section is None:
        _logger.warning(
            "Industry plugin: КИД section %s not found — preset skipped",
            SECTOR_XMLID,
        )
    Chart = env["account.chart.template"]
    for company in env["res.company"].search([]):
        if company.chart_template != "bg":
            continue
        if section and section not in company.l10n_bg_kid_ids:
            company.l10n_bg_kid_ids = [(4, section.id)]
        try:
            Chart._load(
                company.chart_template,
                company,
                install_demo=False,
                force_create=True,
            )
        except Exception as err:  # noqa: BLE001 - log, never block install
            env.cr.rollback()
            _logger.error(
                "Industry plugin: chart reload failed for company %s: %s",
                company.name,
                err,
                exc_info=True,
            )
        else:
            _logger.info(
                "Industry plugin: КИД 'C' preset + chart reloaded for %s",
                company.name,
            )
