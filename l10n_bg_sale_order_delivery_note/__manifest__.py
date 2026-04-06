# -*- coding: utf-8 -*-
# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Bulgarian Sale Order Delivery Note',
    'version': '18.0.1.1.0',
    'category': 'Sales/Bulgaria',
    'summary': 'Generate Accepted Delivery Report for Bulgarian Sale Orders',
    'description': """
       Bulgarian Sale Order Delivery Note
       ==================================

       This module generates "Accepted Delivery Report" (Приемо-предавателен протокол)
       for sale orders in Bulgaria.
       It creates a specialized report template for delivery confirmation documents
       according to Bulgarian business practices.

       Features:
       ---------
       * Generates Accepted Delivery Report for sale orders
       * Bulgarian localization for delivery documentation
       * Compatible with Bulgarian report theme
       * Pro-forma delivery note template
                       """,
    'author': 'Rosen Vladimirov',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'depends': [
        'sale',
        'l10n_bg_report_theme',
        'base_comment_template',
    ],
    'data': [
        'report/ir_action_report_templates.xml',
        'report/ir_actions_report.xml',
    ],
    'demo': [],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'development_status': 'Beta',

    # Metadata
    'tags': ['localization', 'sales', 'bulgaria', 'delivery', 'report'],
    'maintainers': ['rosenvladimirov'],
}
