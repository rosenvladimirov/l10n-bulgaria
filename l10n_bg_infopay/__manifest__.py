# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "InfoPay Integration",
    "summary": "Bank statement sync and payment orders via InfoPay API",
    "version": "18.0.1.1.0",
    "category": "Accounting/Localizations",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "depends": ["account", "l10n_bg_bank_wallet"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "data/ir_cron.xml",
    ],
    "installable": True,
}
