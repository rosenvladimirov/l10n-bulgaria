# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Bulgaria - Accounting enable manual VAT",
    "version": "11.0.1.0.1",
    "author": "Rosen Vladimirov",
    'category': 'Localization',
    "website": "https://github.com/rosenvladimirov/l10n_bg-locales",
    "description": """
This module activate The manual editing VAT on supplier invoice form
    """,
    'depends': [
            'l10n_bg',
    ],
    "demo": [],
    "data": [
            'views/account_invoice_view.xml',
    ],
    "license": "AGPL-3",
    "installable": True,
}
