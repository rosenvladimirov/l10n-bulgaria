# Copyright 2023 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Bulgaria - Cities and Locations",
    "summary": """
            Complete database of Bulgarian cities, municipalities,
            and administrative-territorial units with ЕКАТТЕ codes.""",
    "description": """
Bulgaria - Cities and Locations Database
========================================

This module provides a comprehensive database of Bulgarian geographic locations,
including cities, villages, municipalities, and administrative structures, fully
integrated with the ЕКАТТЕ (Unified Classifier of Administrative-Territorial and
Territorial Units) national standard.

**Core Features**
-----------------

**ЕКАТТЕ Integration**
~~~~~~~~~~~~~~~~~~~~~~
* Full support for ЕКАТТЕ codes (Единен класификатор на административно-
териториалните и територилните единици)
* Official classification system used by Bulgarian National Statistical Institute
* Unique identification codes for all settlements and administrative units
* Enables compliance with Bulgarian administrative standards
* Essential for official reporting and government integration

**Settlement Types Classification**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Comprehensive settlement type taxonomy:
- Cities (град)
- Villages (село)
- Towns (градче)
- Quarters (квартал)
- Monasteries (манастир)
- Railway stations (жп гара)
- And other settlement types
* Translatable type names for multi-language support
* Structured code system for each settlement type

**Administrative Hierarchy**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Three-level administrative structure:

1. **Municipality** (Община)
 - Top-level administrative division
 - Contains multiple settlements
 - Links to regional government

2. **City Hall** (Кметство)
 - Mid-level administrative unit
 - Subdivision of municipality
 - Manages local settlements
 - City hall code tracking

3. **Settlement** (Населено място)
 - Individual cities and villages
 - Links to parent city hall and municipality
 - Standard settlements without administrative function

**Hierarchical Relationships**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Settlement → City Hall → Municipality structure
* Automatic domain filtering for correct hierarchy
* Parent-child relationships between administrative units
* Prevents circular references
* Smart selection lists based on country and structure type

**Tax Office Integration**
~~~~~~~~~~~~~~~~~~~~~~~~~~
* Marking of settlements with NRA (National Revenue Agency) offices
* Support for identifying tax office locations
* Integration point for l10n_bg_tax_offices module
* Enables automatic tax office assignment by location

**Enhanced City Model**
~~~~~~~~~~~~~~~~~~~~~~~
Extends standard Odoo res.city with:
* ЕКАТТЕ code field
* Settlement type classification
* City hall code reference
* Administrative hierarchy links
* Tax office presence indicator
* Structure type identification

**Country State Enhancements**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Translatable state/region names
* Full support for Bulgarian regions (области)
* Multi-language capabilities for all geographic data

**Use Cases**
~~~~~~~~~~~~~
This module is essential for:

**Legal Compliance**
- Official document generation with correct ЕКАТТЕ codes
- Government reporting and submissions
- NRA tax declarations and registrations
- Statistical reporting to NSI (National Statistical Institute)

**Business Operations**
- Accurate address management for Bulgarian partners
- Proper geographic classification of business locations
- Tax office assignment based on location
- Regional sales and operations analysis

**Integration with Other Modules**
- Partner address completion and validation
- Intrastat reporting with correct location codes
- Tax office assignment and reporting
- Regional statistical analysis

**Geographic Analysis**
- Regional breakdown of customers/suppliers
- Sales territory management
- Logistics and delivery planning
- Market analysis by administrative region

**Data Coverage**
~~~~~~~~~~~~~~~~~
Complete Bulgarian geographic database including:
* All 265 municipalities (общини)
* Thousands of city halls (кметства)
* Over 5,000 settlements (cities, towns, villages)
* 28 regions (области)
* Monastery settlements
* Railway station settlements
* All with official ЕКАТТЕ codes

**Technical Features**
~~~~~~~~~~~~~~~~~~~~~~
* Proper model inheritance from res.city
* Smart domain functions for hierarchical filtering
* Index optimization on key fields (name, code, ЕКАТТЕ)
* Translatable content support
* Data import ready structure
* Foreign key relationships with cascading rules

**Integration Points**
~~~~~~~~~~~~~~~~~~~~~~
Works seamlessly with:
* **l10n_bg_config** - Core Bulgarian localization
* **l10n_bg_tax_offices** - NRA office assignment
* **l10n_bg_address_extended** - Enhanced address management
* **partner_multilang** - Transliteration and multi-language names
* **l10n_bg_reports_audit** - Geographic reporting requirements
* **l10n_bg_intrastat** - Location codes for intrastat declarations

**Data Import Support**
~~~~~~~~~~~~~~~~~~~~~~~
* Ready for bulk import of ЕКАТТЕ database
* Structured format for NSI official data
* Update mechanism for ЕКАТТЕ changes
* Maintains data integrity during updates

**Search and Selection**
~~~~~~~~~~~~~~~~~~~~~~~~
Enhanced search capabilities:
* Search by ЕКАТТЕ code
* Search by settlement type
* Filter by administrative hierarchy
* Quick location of tax office settlements
* Multi-language name search

**Compliance Standards**
~~~~~~~~~~~~~~~~~~~~~~~~
Meets requirements for:
* Bulgarian National Statistical Institute (НСИ) standards
* National Revenue Agency (НАП) reporting
* Ministry of Regional Development classifications
* EU geographic coding standards (NUTS)
* Official government document requirements

**Note**: This module significantly improves address management accuracy and
enables full compliance with Bulgarian administrative and statistical standards.
It's a foundational module for any serious Bulgarian localization implementation.
  """,
    "version": "18.0.1.1.1",
    "development_status": "Production/Stable",
    "category": "Localization",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "maintainers": ["rosenvladimirov"],
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "base_address_extended",
        "contacts",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/res_city_types.xml",
        "data/res_country_data.xml",
        "data/ir_cron_data.xml",
        "views/res_city_view.xml",
        "views/l10n_bg_ekatte_sync_views.xml",
    ],
    "demo": [],
    "external_dependencies": {
        "python": ["dbfread", "requests"],
    },
    "post_init_hook": "post_init_hook",
    'images': [
        'static/description/banner.png',
    ],
    "tags": ["localization", "bulgaria", "cities", "ekatte", "geographic"],
    "countries": ["BG"],

    # Version requirements
    'odoo_version': '18.0',
    'python_version': '>=3.11',
}
