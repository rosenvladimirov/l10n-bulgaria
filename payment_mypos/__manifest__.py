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
    "version": "19.4.2.0.0",
    "category": "Accounting/Payment Providers",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "depends": [
        "payment",
        "website_payment",
        # Owner-encrypted credential storage (clientId / clientSecret + future
        # RSA private key). Mirrors the InfoPay 6.0.0 pattern: keys live in
        # the company-owner's crypto.wallet, decrypted with the owner's
        # bcrypt password hash so cron can sudo to the owner and read them.
        "l10n_bg_bank_wallet",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/payment_mypos_templates.xml",
        "views/payment_provider_views.xml",
        "views/mypos_load_credentials_wizard_views.xml",
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
