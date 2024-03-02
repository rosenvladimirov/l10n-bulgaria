# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'L10n Bg Config',
    'summary': """
        This module allows you to install and configure all the localization modules related to Bulgaria.""",
    'version': '16.0.1.0.1',
    'license': 'AGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'depends': [
        'base',
        'account',
        'base_vat',
        'l10n_bg',
    ],
    'data': [
        'views/res_config_view.xml',
        'views/account_account_tag_views.xml',
        'views/partner_view.xml',
        'views/res_company_views.xml',
    ],
    'demo': [
    ],
    "pre_init_hook": 'pre_init_hook',
}
