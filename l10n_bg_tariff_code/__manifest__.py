{
    "name": "Bulgaria Tariff Code Management",
    "summary": "TARIC/HS/CN Code Management with EU API Integration",
    "description": """
Bulgaria Tariff Code Management
===============================

This module provides comprehensive tariff code management for Bulgarian companies.

TARIC Integration
-----------------
* Automatic TARIC code detection from HS/CN/Intrastat codes
* Real-time tariff rate lookup from EU TARIC API system
* Caching mechanism for tariff rates
* Support for multiple countries of origin
* Backward compatibility with HS/CN codes

Product Extensions
------------------
* Tariff code management on products
* Automatic HS code synchronization
* Country of origin tracking
* Tariff rate caching

Invoice Line Features
---------------------
* Automatic tariff code extraction from various sources
* Manual tariff code override
* Tariff rate computation and caching
* Multi-format code normalization (HS6, CN8, CN10)

Company Configuration
---------------------
* TARIC API URL configuration
* API enable/disable setting
* Default tariff rate fallback
* Cache duration management
* Multi-company support

Technical Features
------------------
* Code extraction from text with multiple patterns
* Category-based tariff code inheritance
* Country-specific default rates
* EU country zero-rate support
* Automatic product HS code updates
    """,
    "version": "18.0.3.0.7",
    "category": "Accounting/Localizations",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "account",
        "stock_delivery",
    ],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/l10n_bg_taric_cache.xml",
        "views/account_move_line_views.xml",
        "views/product_template_views.xml",
        "views/res_config_view.xml",
        "wizards/l10n_bg_taric_import_wizard.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
