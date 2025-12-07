# -*- coding: utf-8 -*-
{
    'name': 'Bulgarian Company Registry Integration',
    'version': '18.0.1.1.3',
    'category': 'Contacts',
    'summary': 'Integration with Bulgarian Open Data Portal (data.egov.bg) - Trade Register',
    'description': """
Bulgarian Company Registry Integration
=======================================

This module provides integration with the Bulgarian Open Data Portal (data.egov.bg)
to automatically fetch and populate company information from the Trade Register.

Integrates with l10n_bg_config module to use existing Bulgarian localization fields
and res.transliterate.mixin for multilingual company names.

Uses standard Odoo fields where possible:
- name (translate=True) for multilingual company names
- company_registry for registration numbers
- l10n_bg_uic for EIK/BULSTAT
- vat for VAT numbers

Features:
---------
* Search companies by EIK (Bulgarian company ID)
* Search companies by company name (Bulgarian or English)
* Automatically populate partner data:
  - Multilingual company name (BG/EN via translate=True)
  - Registration number (via standard company_registry field)
  - EIK/UIC (using l10n_bg_uic field)
  - VAT number (using standard vat field with BG prefix)
  - Address (Bulgarian format, translate=True)
  - Legal form
  - Registration date and court
  - Economic activity (NACE code)
* Support for both Bulgarian and English data
* Offline mode with downloaded data cache
* Integration with existing Bulgarian localization (l10n_bg_config)

Technical Details:
------------------
* Uses CKAN API from data.egov.bg
* Works with Trade Register dataset (2df0c2af-e769-4397-be33-fcbe269806f3)
* Supports CSV and JSON data formats
* Can work with downloaded data dumps for offline operation
* Compatible with l10n_bg_config module for UIC/VAT validation

Author: Rosen Vladimirov
License: LGPL-3
    """,
    'author': 'Rosen Vladimirov',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'l10n_bg_config',
        'l10n_bg_city',
    ],
    'data': [
        'views/res_partner_views.xml',
        'wizard/bg_company_search_wizard_views.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'assets': {
        'web.assets_backend': [
            'l10n_bg_company_registry/static/src/js/l10n_bg_uic_widget.js',
            'l10n_bg_company_registry/static/src/xml/l10n_bg_uic_widget.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
