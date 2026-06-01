# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Bulgaria localization Configuration",
    "summary": """
        This module allows you to install and configure all
        the localization modules related to Bulgaria.""",
    "description": """
Bulgaria Localization Configuration - Core Foundation Module
=============================================================

This is the core configuration module for Bulgarian localization in Odoo, providing
the essential infrastructure and utilities required by all other Bulgarian accounting
and localization modules.

**Core Features**
-----------------

**Configuration Management**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Centralized configuration system for all Bulgarian localization modules
* XML-based configuration templates with dynamic parsing
* Company-level settings for Bulgarian accounting compliance
* Multi-company support with per-company configuration
* Encryption system for sensitive API keys and credentials

**Mixin Architecture (l10n.bg.config.mixin)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Abstract model that can be inherited by any Odoo model
* Automatic detection of Bulgarian records based on company settings
* Dynamic view modification - hides Bulgarian fields when not needed
* Smart field visibility control in form, list, and search views
* Context-aware field display based on chart of accounts

**Bulgarian Company Data Management**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Support for Bulgarian Unified Identification Codes (UIC/BULSTAT)
* Multiple identification types:
  - BG UIC (Unified Identification Code/BULSTAT)
  - BG EGN (Personal Identification Number)
  - BG PNF (Personal Number of Foreigner)
  - BG Official Number from NRA
  - BG Unique code under CRA
  - Non-EU Tax Numbers
  - EU VAT Numbers
* Automatic validation using stdnum library
* Representative/Manager contact management
* Tax agent and company agent support
* Department code tracking for NRA reporting

**Partner Extensions**
~~~~~~~~~~~~~~~~~~~~~~
* Enhanced partner types: representative, agent, tax agent
* Automatic UIC/EGN/PNF validation and detection
* API key encryption and management for secure data exchange
* Representative assignment and hierarchy management
* Country-specific title formatting support

**Account Move Enhancements**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Local document numbering system (l10n_bg_name)
* Automatic number formatting to 10-digit standard
* Deal date tracking (separate from invoice date)
* Bulgarian document date management
* Smart number extraction from various formats

**Account Tag Descriptions**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Translatable descriptions for account tags
* Enhanced tax reporting metadata
* Better audit trail documentation

**Chart of Account Template System**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Plugin-based architecture for chart template extensions
* Dynamic CSV parsing for accounts, groups, and taxes
* Modular plugin loading from installed modules (l10n_bg_config_plugins_*)
* Account code masking system with flexible formatting
* Automatic code padding and formatting (e.g., ###.### format)
* Template inheritance and override support
* Centralized data management for accounts, groups, taxes, journals

**Multi-language Support**
~~~~~~~~~~~~~~~~~~~~~~~~~~
* Tracking of installed multilanguage modules
* JSON-based configuration for multilanguage settings
* Integration with partner_multilang and l10n_bg_multilang
* State tracking for multilanguage module activation

**Security & Encryption**
~~~~~~~~~~~~~~~~~~~~~~~~~
* API key generation with customizable templates
* XOR-based encryption for sensitive credentials
* Base64 encoding for secure storage
* Company-specific encryption keys
* Automatic key generation when not provided

**Module Dependency Management**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides configuration options for installing related modules:
* Currency Rate Update (OCA & EE versions)
* Bulgarian Cities and Locations
* Extended Address Management
* NRA Tax Offices and Departments
* Intrastat Product Declaration (OCA)
* Partner Transliteration (ISO9)
* Multi-register Identification Codes
* Accounting Tax Audit Reports
* Intrastat Reporting (EE)
* Asset Management with Bulgarian rules
* Report Themes
* VAT Reports and Export Files (OCA & EE)

**Technical Infrastructure**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Pre-init and post-init hooks for setup automation
* Auto-install when l10n_bg is present
* External dependency: xmltodict for XML processing
* Backend assets for enhanced UI components
* Proper tags for discoverability: localization, accounting, bulgaria
* Country code: BG
* Python 3.12+ required
* Odoo 19.0 compatible

**Wizard Tools**
~~~~~~~~~~~~~~~~
* Account tag bulk edit wizard
* Settings preview with XML file support
* Chart template plugin installer
* Multilanguage settings viewer with JSON formatting

**View Enhancements**
~~~~~~~~~~~~~~~~~~~~~
* Automatic field hiding for non-Bulgarian companies
* Context-sensitive UI elements
* Enhanced configuration settings interface
* Representative contact selection
* Department code configuration

**Use Cases**
~~~~~~~~~~~~~
This module is essential for:
- Setting up Bulgarian accounting in Odoo
- Managing multiple Bulgarian companies
- Integrating with NRA systems
- Preparing for Bulgarian tax reporting
- Ensuring compliance with Bulgarian commercial law
- Building custom Bulgarian localization plugins

**Integration Points**
~~~~~~~~~~~~~~~~~~~~~~
* Works as foundation for all l10n_bg_* modules
* Provides base classes and mixins for inheritance
* Supplies configuration infrastructure
* Manages module state and dependencies
* Handles data encryption for secure API integrations

**Note**: This module requires l10n_bg (Bulgarian Chart of Accounts) and
automatically installs it if not present. It serves as the configuration
backbone for the entire Bulgarian localization ecosystem.
    """,
    "version": "19.0.8.6.3",
    # OCA Metadata
    "development_status": 'Beta',
    "category": 'Localization',
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "base",
        "bus",
        "mail",
        "account",
        "base_vat",
        "l10n_bg",
        "l10n_bg_ledger",
    ],
    'external_dependencies': {
        'python': ['xmltodict', 'cryptography'],
    },
    "data": [
        "data/res_lang_data.xml",
        "security/ir.model.access.csv",
        "data/l10n.bg.kid.csv",
        "data/l10n_bg_vertical_data.xml",
        "wizards/account_account_tag_bulk_edit_wizard.xml",
        "wizards/account_settings_preview_xml_file.xml",
        "wizards/account_chart_template_plugins.xml",
        "wizards/l10n_bg_kid_compute_wizard.xml",
        "wizards/l10n_bg_vertical_wizard.xml",
        "views/res_config_view.xml",
        "views/account_account_tag_views.xml",
        "views/partner_view.xml",
        "views/res_company_views.xml",
        "views/account_move_views.xml",
        "views/l10n_bg_kid_views.xml",
    ],
    "demo": [],
    'images': [
        'static/description/banner.png',
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_bg_config/static/src/**/*",
        ],
    },
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    # NB: stock Odoo does NOT honor a 'post_migrate_hook' manifest key
    # (only OpenUpgrade does). Upgrade-time backfill lives in
    # migrations/<version>/post-migrate.py instead.
    "auto_install": ["l10n_bg"],

    'tags': ['localization', 'accounting', 'bulgaria', 'configuration'],
    "countries": ["BG"],

    # Version requirements
    'odoo_version': '19.0',
    'python_version': '>=3.12',
}
