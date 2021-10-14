# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from odoo import api, SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """
    With this pre-init-hook we want to add new language sensitive column to fix problem with different from latin letters words
    """
    cr.execute("""SELECT installed_version FROM pg_available_extensions WHERE name = 'pg_trgm';""")
    res = cr.fetchone()
    # _logger.info('INIT %s' % res)
    if res and not res[0]:
        cr.execute("""CREATE EXTENSION pg_trgm;""")
        cr.execute("SELECT set_limit(0.2);")

    cr.execute("""SELECT column_name FROM information_schema.columns WHERE table_name='res_partner' AND column_name='display_name_bg'""")
    if not cr.fetchone():
        cr.execute("""ALTER TABLE res_partner ADD COLUMN display_name_bg character varying;""")

    cr.execute("""SELECT column_name FROM information_schema.columns WHERE table_name='res_partner' AND column_name='display_name_en'""")
    if not cr.fetchone():
        cr.execute("""ALTER TABLE res_partner ADD COLUMN display_name_en character varying;""")

    cr.execute("""SELECT column_name FROM information_schema.columns WHERE table_name = 'res_partner' AND column_name = 'display_name_el'""")
    if not cr.fetchone():
        cr.execute('ALTER TABLE res_partner '
                   'ADD COLUMN display_name_el character varying;')


def post_init_hook(cr, registry):
    #{'lang': 'bg_BG', 'type': 'model', 'name': 'res.partner,street_name', 'res_id': 130, 'value': 'КЛИМЕНТ ОХРИДСКИ', 'src': 'KLIMENT OHRIDSKI ', 'state': 'translated'}
    env = api.Environment(cr, SUPERUSER_ID, {})
    country = env.user.company_id.country_id
    if country.code == 'bg_BG':
        cities = env['res.city'].search([('country_id', '=', country.id)])
        for city in cities:
            translate = env['is.translation'].search(('name', '=', 'res.city,name'), ('lang', '=', 'bg_BG'), ('type', '=', 'model'), ('res_id', '=', city.id))
            if not translate:
                #city.with_context(lang='bg').write({'name': city.name})
                trans = env.get('l10n_bg_multilang.transliterate').transliterate(city.name)
                translate.create({'lang': 'bg_BG', 'type': 'model', 'name': 'res.city,name', 'value': city.name, 'src': trans, 'source': trans, 'state': 'translated'})
