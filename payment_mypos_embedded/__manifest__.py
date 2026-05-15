# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Payment Provider: myPOS — Embedded Checkout",
    "summary": "On-site iFrame checkout for myPOS (no redirect)",
    "description": """
Complementary flow for ``payment_mypos``: instead of redirecting the
shopper to the myPOS hosted page, the myPOS Embedded SDK mounts a
branded iFrame directly in the Odoo checkout page.

Key differences vs the redirect flow:
  * No client-side RSA signature — the Embedded SDK only carries
    sid / walletNumber / keyIndex; security comes from the signed
    server-to-server urlNotify callback (verified by payment_mypos's
    existing controller + _mypos_verify).
  * Supported schemes: Visa, Visa Electron, Mastercard, Maestro.
    Apple Pay / Google Pay are NOT available in Embedded checkout.
  * Better conversion (shopper never leaves the site).

Switch a provider to embedded via the new "Checkout Flow" field on
the myPOS payment provider.
""",
    "version": "18.0.1.0.0",
    "category": "Accounting/Payment Providers",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "depends": [
        "payment_mypos",
    ],
    "data": [
        "views/payment_mypos_embedded_templates.xml",
        "views/payment_provider_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_mypos_embedded/static/src/js/embedded_checkout.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
