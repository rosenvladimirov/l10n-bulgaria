# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizards

from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    _preserve_tag_on_taxes(cr, registry)
    # {'lang': 'bg_BG', 'type': 'model', 'name': 'res.partner,street_name', 'res_id': 130, 'value': 'КЛИМЕНТ ОХРИДСКИ', 'src': 'KLIMENT OHRIDSKI ', 'state': 'translated'}
    env = api.Environment(cr, SUPERUSER_ID, {})
    country = env.user.company_id.country_id
    country_code = country.code


def _preserve_tag_on_taxes(cr, registry):
    from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes
    preserve_existing_tags_on_taxes(cr, registry, 'l10n_bg')
