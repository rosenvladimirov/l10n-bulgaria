# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Bulgaria - Accounting Expense Tracker",
    "version": "11.0.1.0",
    "author": "Rosen Vladimirov",
    'category': 'Localization',
    "website": "https://github.com/rosenvladimirov/l10n_bg-locales",
    "description": """
This is the module to manage the Accounting Expense Tracker
===========================================================

Bulgarian account Expense Tracker.
    """,
    'depends': [
        'l10n_bg',
        'hr_expense',
    ],
    'external_dependencies': {'python': ['xlrd']},
    "demo": [],
    "data": [

    ],
    "license": "AGPL-3",
    "installable": True,
}
