# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bulgaria - Accounting - Tax Administration rules',
    'icon': '/l10n_bg/static/description/icon.png',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Rosen Vladimirov <vladimirov.rosen@gmail.com>,Odoo Community Association (OCA)',
    'description': """
        Tax administration rules:
        1. Numbering of documents.
        2. ....
    """,
    'depends': [
        'account',
        'l10n_bg',
        'l10n_bg_config',
        'account_debit_note',
        'account_move_fiscal_month',
        'date_range',
        'account_account_tag_code',
        'account_financial_forms',
    ],
    'data': [
        'views/account_move_views.xml',
        'views/l10n_bg_protocol_account_move.xml',
        'views/res_currency_views.xml',
    ],
    'demo': [
    ],
    'license': 'LGPL-3',
}
