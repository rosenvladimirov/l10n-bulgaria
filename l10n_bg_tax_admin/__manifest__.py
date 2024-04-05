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
        'account_debit_note',
        'l10n_bg',
        'l10n_bg_config',
        # 'account_financial_forms', moved in l10n_bg_account_financial_forms
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/l10n_bg_tax_admin_pre_functions.xml',
        'data/l10_bg_chart_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_fiscal_position_template.xml',
        'data/l10n_bg_tax_admin_post_functions.xml',
        'views/account_chart_template_views.xml',
        'views/account_move_views.xml',
        'views/account_journal_views.xml',
        'views/l10n_bg_protocol_account_move.xml',
        'views/res_currency_views.xml',
        'views/partner_view.xml',
        'views/product_view.xml',
    ],
    'demo': [
    ],
    'license': 'LGPL-3',
    # 'pre_init_hook': 'pre_init_hook',
    # 'post_init_hook': 'post_init_hook'
}
