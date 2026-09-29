# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Telegram Bot: Sales",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Sell from the Telegram bot: packages, shop checkout, vouchers, balance",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd., "
    "Odoo Community Association (OCA)",
    "maintainers": ["rosen-vladimirov"],
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria/tree/19.0/"
    "l10n_bg_telegram_bot_sale",
    "license": "LGPL-3",
    "depends": [
        "l10n_bg_telegram_bot",
        "website_sale",
        "sale_loyalty",
        "sale_timesheet",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/l10n_bg_telegram_bot_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
