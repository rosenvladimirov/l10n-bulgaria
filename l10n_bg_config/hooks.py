#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv
import io
import logging
import os

import odoo
from odoo.tools.translate import load_language

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate_account_account_tag(env):
    country_id = env.ref('base.bg').id
    tag_model = env['account.account.tag'].with_context(lang='en_US')
    tag_ids = tag_model.search([('applicability', '=', 'taxes'), ('country_id', '=', country_id)])
    module = __name__.split("addons.")[1].split(".")[0]
    module_path = ""
    for adp in odoo.addons.__path__:
        module_path = adp + os.sep + module
        if os.path.isdir(module_path):
            break
    _logger.info(f"{module_path}")
    module_path += os.sep + "data" + os.sep
    with io.open(
        module_path + 'account_account_tag.csv', mode="r") as AAT_file:
        tag_file_ids = csv.DictReader(AAT_file, delimiter=";")
        for tag in tag_file_ids:
            tag_id = tag_ids.filtered(lambda r: r.name == tag['name'])
            if tag_id:
                tag_id.write({
                    'description': tag['description'],
                    'l10n_bg_applicability': tag['l10n_bg_applicability'],
                })
    lang = env['ir.model.data'].search([
        ('module', '=', 'base'),
        ('name', '=', 'lang_bg'),
    ])
    if lang:
        lang.noupdate = False

def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    migrate_account_account_tag(env)
    modules = env['ir.module.module'].search([('state', '=', 'installed')])
    for lang in ['base.lang_bg', 'base.lang_en']:
        res_id = env.ref(lang, raise_if_not_found=False)
        language = env['res.lang'].search([('id', '=', res_id.id), ('active', '=', False)])
        if language:
            load_language(cr, language.code)
            modules._update_translations(language.code)
