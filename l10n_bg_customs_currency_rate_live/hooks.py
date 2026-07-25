#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.l10n_bg_customs_currency_rate_live.models.res_config_settings_fix import ResCompany
from odoo.addons.currency_rate_live.models.res_config_settings import ResCompany as rescompany

def post_load_hook():
    rescompany._generate_currency_rates = ResCompany._generate_currency_rates
