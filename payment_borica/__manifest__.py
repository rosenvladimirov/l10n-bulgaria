# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Payment Provider: Borica APGW (BG)",
    "summary": "Accept card payments via Borica APGW (CGI v4.0, EMV 3DS 2.x)",
    "description": """
Borica APGW payment provider for Odoo eCommerce, Sales and Invoicing.

Implements the Borica e-Gateway CGI/WWW Forms interface v4.0 with the
MAC_GENERAL signing scheme — accepts bcard, Visa, Mastercard, Diners and
Discover cards through 3-D Secure (EMV 3DS v2.1 / v2.2).

Designed for Bulgarian merchants with a vPOS contract from any of the
local acquirer banks routing through Borica.
""",
    "version": "18.0.1.0.0",
    "category": "Accounting/Payment Providers",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "depends": [
        "payment",
        "website_payment",
    ],
    "data": [
        "views/payment_borica_templates.xml",
        "views/payment_provider_views.xml",
        "data/payment_provider_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_borica/static/src/js/payment_form.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
