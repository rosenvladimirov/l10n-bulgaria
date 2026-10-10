import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# Мостовете на издателя при печат (print.signer.mixin) са auto_install, но
# Odoo ги поставя само когато се ИНСТАЛИРА зависимост — при `-u l10n_bg_config`
# на база, където sale/purchase/stock вече са вътре, остават `uninstalled`
# (мерено 10.10.2026, база signer_upg). Тогава поръчките и трансферите остават
# без `print_signer_id` и отчетите, които го викат, гърмят.
#
# Затова при ъпгрейд маркираме за инсталация онези мостове, чиито зависимости
# вече са инсталирани; loader-ът ги поема в същия пробег (loading.py: цикълът
# по 'to install').
BRIDGES = ("l10n_bg_config_sale", "l10n_bg_config_purchase", "l10n_bg_config_stock")


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Module = env["ir.module.module"]
    Module.update_list()
    for bridge in Module.search([("name", "in", BRIDGES), ("state", "=", "uninstalled")]):
        deps = bridge.dependencies_id.depend_id
        if deps and all(dep.state in ("installed", "to upgrade") for dep in deps):
            bridge.button_install()
            _logger.info("l10n_bg_config: мостът %s е маркиран за инсталация", bridge.name)
