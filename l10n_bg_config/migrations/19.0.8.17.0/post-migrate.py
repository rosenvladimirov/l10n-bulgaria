import logging

from odoo import SUPERUSER_ID, api

from odoo.addons.l10n_bg_config.hooks import fix_ica_ptc_group

_logger = logging.getLogger(__name__)

# До 19.0.8.16.0 data/template/account.tax-bg.csv презаписваше данъка на
# ядрото l10n_bg_purchase_vat_20_ptc_ica (ВОП с ЧДК) като група с клиринг през
# 430 и начислен ДДС с таг 21 (кл. 21) вместо 22 (кл. 22 — ДДС за ВОП, ППЗДДС,
# Приложение № 13). Редът в CSV-то е махнат, така че новите фирми получават
# данъка на ядрото; тук поправяме вече създадените. Осчетоводените редове не
# се пипат, старите деца се архивират.


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    fixed = fix_ica_ptc_group(env)
    _logger.info("l10n_bg_config: %s ICA PTC tax(es) restored from l10n_bg", len(fixed))
