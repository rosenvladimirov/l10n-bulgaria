{
    'name': 'Bulgaria Tax Assistant',
    'summary': """This is a technical module that adds the necessary functionalities required by Bulgarian legislation.""",
    'description': """
Bulgaria Tax Assistant - Advanced VAT and Customs Management
============================================================

This module extends Odoo's accounting capabilities to comply with Bulgarian tax legislation,
providing comprehensive support for:

**VAT Protocols (Article 117, paragraph 2)**
--------------------------------------------
* Protocol generation for reverse charge transactions
* Protocol generation for self-supply/private usage with consumption coefficients
* Automatic calculation based on personal vs. total consumption metrics
* Support for different measurement units (kilometers, hours)

**Customs Declarations**
------------------------
* Full customs declaration management with TARIC integration
* Automatic tariff code detection from HS/CN/Intrastat codes
* Real-time tariff rate lookup from EU TARIC API system
* Support for customs procedures and nomenclatures (transport, packaging, documents)
* Multi-currency customs value calculation with configurable rates
* Tracking of gross/net weight and country of origin
* Customs expense distribution and management

**Fiscal Position Extensions**
------------------------------
* Advanced tax action mapping for different document types
* Automatic document type detection and narration
* Support for multiple transaction types: standard, customs, protocol, private usage
* Configurable replacement fiscal positions and accounts

**Enhanced Tax Calculation**
----------------------------
* Custom tax types: customs_rate and private_rate
* Dynamic base amount calculation for customs declarations
* Consumption coefficient application for private usage
* Integration with existing tax computation engine

**Product Extensions**
----------------------
* Tariff code management with backward compatibility
* Automatic HS code synchronization
* Customs expense marking
* Country of origin tracking

**TARIC API Integration**
-------------------------
* Configurable API connection to European TARIC system
* Automatic caching of tariff rates (configurable duration)
* Fallback to default rates when API unavailable
* Support for multiple countries and duty expressions

**Company Configuration**
-------------------------
* TARIC API URL and enablement settings
* Default tariff rate configuration
* Cache duration management
* Multi-company support

**Technical Features**
----------------------
* Sequence management for protocols, private documents, and customs declarations
* Mail tracking and activity management
* Inheritable models with proper _inherits usage
* Compute/inverse/store pattern for complex fields
* Integration with l10n_bg_reports_audit for audit trail

This module is essential for Bulgarian companies dealing with:
- Import/export operations
- Reverse charge VAT transactions
- Private usage of company assets
- Cross-border trade within and outside EU
    """,
    'version': '18.0.9.0.7',
    "category": "Accounting/Localizations/Reporting",
    "development_status": "Beta",
    "license": "OPL-1",
    'author': 'Rosen Vladimirov',
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria-ee",
    'depends': [
        'account',
        'stock',
        'stock_landed_costs',
        'l10n_bg_config',
        'l10n_bg_reports_audit',
        'l10n_bg_tax_offices',
        'l10n_bg_tariff_code',
        "l10n_bg_ledger",
        'markdown_viewer_locale',
    ],
    'data': [
        'data/product_template_data.xml',
        'data/l10n_bg_customs_nomenclature.xml',
        'security/ir.model.access.csv',
        'views/account_fiscal_position_tax_action.xml',
        'views/account_move_views.xml',
        'views/account_move_line_views.xml',
        'views/account_move_bg_protocol.xml',
        'views/account_move_bg_private.xml',
        'views/account_move_bg_customs_views.xml',
        'views/l10n_bg_customs_nomenclature_views.xml',
        'views/partner.xml',
        'views/product_template_views.xml',
        'views/report_protocol.xml',
        'views/report_private.xml',
        'views/reports.xml',
    ],
    'demo': [
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_bg_tax_admin/static/src/scss/customs_fields.scss',
            'l10n_bg_tax_admin/static/src/components/tax_total_signed/tax_total_signed.js',
            'l10n_bg_tax_admin/static/src/components/tax_total_signed/signed_tax_total.xml',
            # Добавяме регистрацията на документацията
            ('after', 'markdown_viewer_locale/static/src/js/markdown_registry.js',
             'l10n_bg_tax_admin/static/src/js/l10n_bg_tax_admin_markdown.js'),
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    "price": 300,
    "price_currency": "EUR",
}
