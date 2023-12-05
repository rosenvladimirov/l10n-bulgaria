# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bulgaria - Accounting - Tax Administration rules',
    'icon': '/l10n_bg/static/description/icon.png',
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Odoo S.A.',
    'description': """
        Tax administration rules:
        1. Numbering of documents.
        2. ....
    """,
    'depends': [
        'account',
        'l10n_bg',
        'account_debit_note',
        'account_move_fiscal_month',
        'date_range',
        'account_account_tag_code',
        'account_financial_forms',
    ],
    'data': [
        'views/account_move_views.xml',
        'views/res_currency_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
    ],
    'license': 'LGPL-3',
}
