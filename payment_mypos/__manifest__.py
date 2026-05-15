# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Payment Provider: myPOS",
    "summary": "Accept card payments via myPOS Checkout API (REST + 3DS)",
    "description": """
myPOS payment provider for Odoo eCommerce, Sales and Invoicing.

Integrates the myPOS Checkout API v1.4.1 — accepts Visa, Mastercard, JCB,
Bancontact and other supported card schemes through 3D Secure flows.

Designed for use in 30+ EU countries where myPOS operates.
""",
    "version": "19.0.1.2.0",
    "category": "Accounting/Payment Providers",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "depends": [
        "payment",
        "website_payment",
    ],
    "data": [
        "views/payment_mypos_templates.xml",
        "views/payment_provider_views.xml",
        "data/payment_provider_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_mypos/static/src/js/payment_form.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
