# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name" : "Fixes for all labels",
    "version" : "11.0.2.0",
    "author" : "Rosen Vladimirov",
    'category': 'Localization',
    "description": """
Fixes for barcode, package labels.
    """,
    'conflicts': [],
    'depends': [
        'stock',
        'l10n_bg',
        'report_theming',
    ],
    "demo" : [],
    "data" : [
              'data/report_paperformat.xml',
              'data/ir_actions_report.xml',
              'views/report_templates.xml',
              'views/report_package_barcode.xml',
              'views/stock_report_views.xml',
              ],
    'license': 'AGPL-3',
    "installable": True,
}
