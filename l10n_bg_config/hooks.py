#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools.translate import load_language

from odoo import SUPERUSER_ID, api


def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    modules = env['ir.module.module'].search([('state', '=', 'installed')])
    for lang in ['base.lang_bg', 'base.lang_en']:
        res_id = env.ref(lang, raise_if_not_found=False)
        language = env['res.lang'].search([('id', '=', res_id.id), ('active', '=', False)])
        if language:
            load_language(cr, language.code)
            modules._update_translations(language.code)
