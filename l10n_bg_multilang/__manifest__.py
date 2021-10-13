# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Multi Language Partner, Company, Employee',
    'version': '11.0.0.2.0',
    "author" : "Rosen Vladimirov",
    'category': 'Localization',
    'description': """
    * Multi language support for Partner, Company, Employee.
    """,
    'depends': [
        'base',
        'hr',
        'stock',
        'l10n_multilang',
        'base_search_fuzzy',
        'partner_academic_title',
    ],
    'data': [
        "data/trgm_index_data.xml",
        'views/res_country_view.xml',
        'views/res_partner_view.xml'
    ],
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
}

