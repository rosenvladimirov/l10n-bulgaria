# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Add trustee partner",
    "version" : "11.0.2.0",
    "author" : "Rosen Vladimirov",
    'category': 'Localization',
    "description": """
This is the module to manage the Additional functionality for trustee partner.
==============================================================================

In some situations, it is necessary to transfer money through an intermediary,
which is mainly the intermediary for payments, such as Speditors, PayWal, WesternUnion and others.
This module adds a new account for such operations, called a trustee, and in the payee account.
In order to work correctly, it is necessary to create a bank / cash jornal with transit account.
    """,
    'depends': [
        'base',
        'account',
        'l10n_bg',
    ],
    "demo" : [],
    "data" : [
              'views/res_partner_views.xml',
              'views/account_payment_view.xml',
              ],
    'license': 'Other proprietary',
    "installable": True,
}
