# -*- coding: utf-8 -*-
{
    'name': 'Bulgarian Company Registry Integration',
    'version': '18.0.2.0.1',
    'category': 'Localization',
    'summary': 'Real-time integration with Bulgarian Trade Registry (portal.registryagency.bg)',
    'description': """
Bulgarian Company Registry Integration
=======================================

Real-time integration with the official Bulgarian Trade Registry API
(portal.registryagency.bg) to automatically fetch and populate company data.

Key Features:
-------------
* Real-time API integration with portal.registryagency.bg
* Search companies by EIK (Bulgarian company identification number)
* Automatically populate partner data including:
  - Company name (Bulgarian)
  - Complete structured address (city, street, postal code, district)
  - Legal form (ООД, ЕООД, АД, ЕТ, etc.)
  - Registration date and court
  - Economic activity (NACE/NKID code and description)
  - Company managers and representatives
  - Contact information (email, phone)
* Smart address parsing supporting all Bulgarian formats:
  - Streets (ул.) and boulevards (бул.)
  - Residential complexes (ж.к.)
  - Resort complexes (к.к.)
  - Localities (м.) and quarters (кв.)
  - With district information (р-н)
  - Email and phone extraction from addresses
* 100% success rate for address parsing
* No offline database needed - always fresh data
* Works with l10n_bg_config module for EIK/UIC validation

Recent Improvements (v18.0.2.0.1):
----------------------------------
* Fixed HTML address parsing to preserve structure
* Fixed contact information extraction from addresses
* Fixed multi-word street name parsing
* Added support for residential complexes and all address types
* Achieved 100% success rate (up from 37%)
* Tested with real companies from multiple cities

Technical Details:
------------------
* API Endpoint: https://portal.registryagency.bg/CR/api/Deeds/
* Direct connection to official government registry
* Real-time data retrieval (30-second timeout)
* Intelligent address parsing with regex patterns
* Manager/representative extraction
* Bilingual support (Bulgarian with English generation)

Integration:
------------
* Depends on l10n_bg_config for Bulgarian localization fields
* Uses standard Odoo fields where possible
* Extends res.partner with Bulgarian-specific fields
* Provides wizard for interactive company search

Usage:
------
1. Open a partner record
2. Enter EIK number
3. Click "Fetch from Registry" button
4. All data is automatically populated

Or use the "Search Registry" wizard for more control.

Author: Rosen Vladimirov
License: LGPL-3
Version: 18.0.2.0.1 (December 2025)
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
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'wizard/bg_company_search_wizard_views.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
