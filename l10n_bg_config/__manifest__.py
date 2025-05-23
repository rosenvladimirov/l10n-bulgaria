# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Bulgaria localization Configuration",
    "summary": """
        This module allows you to install and configure all
        the localization modules related to Bulgaria.""",
    "version": "18.0.3.0.0",
    # OCA Metadata
    "development_status": 'Beta',
    "license": "AGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "depends": [
        "base",
        "account",
        "base_vat",
        "l10n_bg",
    ],
    "data": [
        "data/res_lang_data.xml",
        "views/res_config_view.xml",
        "views/account_account_tag_views.xml",
        "views/partner_view.xml",
        "views/res_company_views.xml",
        "views/account_move_views.xml",
    ],
    "demo": [],

    'images': [
        'static/description/banner.png',
    ],

    "assets": {
        "web.assets_backend": [
            "l10n_bg_config/static/src/**/*",
        ],
    },
    "pre_init_hook": "pre_init_hook",
    'post_init_hook': 'post_init_hook',
    "auto_install": ["l10n_bg"],

    'tags': ['localization', 'accounting', 'bulgaria', 'configuration'],

    # Version requirements
    'odoo_version': '18.0',
    'python_version': '>=3.11',
}
