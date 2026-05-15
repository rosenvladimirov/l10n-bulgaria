# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "InfoPay Integration",
    "summary": "Bank statement sync, payment orders and invoice issuance "
               "via the Borica InfoPay API",
    "version": "18.0.6.0.8",
    "category": "Accounting/Localizations",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "depends": [
        "l10n_bg_queue_poll",
        "account",
        "l10n_bg_config",
        "l10n_bg_bank_wallet",
    ],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "data/account_payment_method.xml",
        "data/ir_cron.xml",
        "views/account_journal_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
}
