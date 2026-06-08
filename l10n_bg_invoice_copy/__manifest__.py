# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Bulgarian Invoice Copy',
    'version': '19.4.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Add COPY watermark to Bulgarian invoice reports',
    'description': """
        This module adds a "COPY" watermark to invoice reports in Bulgaria.
        It inherits the standard invoice report template and adds the copy designation.
    """,
    'depends': [
        'account',
        'l10n_bg_report_theme',
    ],
    'data': [
        'views/report_invoice_copy.xml',
    ],
    'demo': [],
    "license": "AGPL-3",
    'installable': True,
    'application': False,
    'auto_install': False,
}
