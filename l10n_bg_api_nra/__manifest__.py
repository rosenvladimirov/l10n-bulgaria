{
    "name": "Bulgaria - NRA API Integration",
    "summary": "Core module for submitting declarations to the Bulgarian National Revenue Agency (НАП) via public API",
    "description": """
Bulgaria - NRA API Integration
==============================

Core module providing infrastructure for automated submission of declarations
to the Bulgarian National Revenue Agency (НАП) through their public REST API
at https://public-api.nra.bg/.

Core Features
-------------
* OAuth 2.0 authentication with NRA API (client credentials grant)
* Rate limiting handling (token bucket: 15 burst, 5/s replenish)
* Base declaration model with full workflow (draft → submitted → accepted/rejected)
* XML payload generation and XSD validation framework
* Submission status tracking with NRA document/incoming numbers

Supported Declaration Types
----------------------------
* **Декларация обр. 1** — Data for insured persons (Данни за осигурените лица)
* **Декларация обр. 6** — Due contributions and income tax (Дължими вноски и данък по ЗДДФЛ)
* **ДДС** — VAT declarations
* **VIES** — Intra-community supply declarations

ETZ (Electronic labor records) is provided by the separate
``l10n_bg_api_nra_etz`` EE module.

API Key Acquisition
-------------------
1. Log in to https://portal.nra.bg/ with a Qualified Electronic Signature (КЕП)
2. Navigate to "Управление на достъпи система-система"
3. Select "Достъп до услуги на НАП през API"
4. Submit "Ново заявление за достъп до API"
5. API key is generated automatically (valid up to 365 days)

Technical Infrastructure
------------------------
* REST API with OAuth 2.0 bearer tokens
* XML payloads validated against NRA-published XSD schemas
* Automatic retry with exponential backoff on HTTP 429 (rate limit)
* Structured error handling and logging
    """,
    "version": "18.0.1.3.0",
    "development_status": "Beta",
    "category": "Localization",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "base",
        "mail",
        "hr",
        "l10n_bg_config",
        "l10n_bg_bank_wallet",
    ],
    "external_dependencies": {
        "python": [
            "requests",
            "lxml",
        ],
    },
    "data": [
        "security/nra_security.xml",
        "security/ir.model.access.csv",
        "data/nra_data.xml",
        "wizards/nra_credentials_wizard_views.xml",
        "views/res_company_views.xml",
        "views/nra_declaration_views.xml",
        "views/nra_declaration_h18_views.xml",
        "views/hr_employee_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_bg_api_nra/static/src/js/kep_signer.js",
            "l10n_bg_api_nra/static/src/js/sign_submit_dialog.js",
            "l10n_bg_api_nra/static/src/js/sign_submit_widget.js",
            "l10n_bg_api_nra/static/src/xml/sign_submit_dialog.xml",
        ],
    },
    "demo": [],
    "installable": True,
    "auto_install": False,
    "countries": ["BG"],
    "tags": [
        "localization",
        "accounting",
        "bulgaria",
        "nra",
        "api",
        "declarations",
    ],
}
