import logging

_logger = logging.getLogger(__name__)


def post_init_reload_chart(env):
    """Reload the chart template for every company that already has one,
    so the КИД ↔ account mapping shipped by this plugin is materialised
    on existing databases (same pattern as the other
    ``l10n_bg_config_plugins_*`` data plugins)."""

    Chart = env["account.chart.template"]

    for company in env["res.company"].search([]):
        if not company.chart_template:
            continue
        try:
            Chart._load(
                company.chart_template,
                company,
                install_demo=False,
                force_create=True,
            )
            _logger.info("Chart template reloaded for company %s", company.name)
        except Exception as err:  # noqa: BLE001 - log, never block install
            env.cr.rollback()
            _logger.error(
                "Chart reload failed for company %s: %s",
                company.name,
                err,
                exc_info=True,
            )
