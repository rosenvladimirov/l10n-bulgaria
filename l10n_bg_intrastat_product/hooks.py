#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import shutil
import csv
import io
import os
import odoo

from odoo.api import Environment, SUPERUSER_ID


def pre_init_hook(cr):
    module = 'intrastat_product_hscodes_import'
    module_path = ""
    for adp in odoo.addons.__path__:
        module_path = adp + os.sep + module
        if os.path.isdir(module_path):
            break
    source_module = __name__.split("addons.")[1].split(".")[0]
    source_path = ""
    for adp in odoo.addons.__path__:
        source_path = adp + os.sep + source_module
        if os.path.isdir(source_path):
            break
    module_path += os.sep + "static/data" + os.sep
    source_path += os.sep + "data" + os.sep
    if not os.path.isfile(module_path + '2023_bg_intrastat_codes.csv'):
        shutil.copy2(source_path + '2023_bg_intrastat_codes.csv', module_path + '2023_bg_intrastat_codes.csv')


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    module = __name__.split("addons.")[1].split(".")[0]
    module_path = ""
    for adp in odoo.addons.__path__:
        module_path = adp + os.sep + module
        if os.path.isdir(module_path):
            break
    module_path += os.sep + "data"

    with io.open(file=os.path.join(module_path, 'intrastat.transaction.bg.csv'), mode='r') as csv_file:
        cn_codes = csv.DictReader(csv_file, delimiter=';')
        for row in cn_codes:
            res_id = env.ref(row['id'])
            if res_id:
                res_id = env['intrastat.transaction'].search([('id', '=', res_id.id)])
                if res_id:
                    res_id.with_context(lang='bg_BG').write({
                        'description': row['description'],
                    })

    with io.open(file=os.path.join(module_path, 'intrastat.region.bg.csv'), mode='r') as csv_file:
        cn_codes = csv.DictReader(csv_file, delimiter=',')
        for row in cn_codes:
            country_id = env.ref('base.bg')
            state_code_id = env['res.country.state'].search([
                ('country_id', '=', country_id.id),
                ('code', '=', row['code'].strip())
            ])
            res_id = env.ref(row['id'])
            if res_id:
                res_id = env['intrastat.region'].search([('id', '=', res_id.id)])
                if res_id:
                    res_id.with_context(lang='bg_BG').write({
                        'name': row['name'],
                        'description': row['description'],
                    })
            if state_code_id:
                for city in env['res.city'].search([('country_id', '=', country_id.id),
                                                    ('state_id', '=', state_code_id.id)]):
                    city.write({
                      'region_id': res_id.id,
                    })

    with io.open(file=os.path.join(module_path, 'intrastat.transport_mode.bg.csv'), mode='r') as csv_file:
        cn_codes = csv.DictReader(csv_file, delimiter=';')
        for row in cn_codes:
            res_id = env.ref(row['id'])
            if res_id:
                res_id = env['intrastat.transport_mode'].search([('id', '=', res_id.id)])
                if res_id:
                    res_id.with_context(lang='bg_BG').write({
                        'name': row['name'],
                        'description': row['description'],
                    })

