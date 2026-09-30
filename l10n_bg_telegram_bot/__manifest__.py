# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Telegram Bot (base)",
    "version": "19.0.1.3.0",
    "category": "Technical",
    "summary": "Telegram bot from BotFather driven by Odoo: webhook, users, commands",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd., "
    "Odoo Community Association (OCA)",
    "maintainers": ["rosen-vladimirov"],
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria/tree/19.0/l10n_bg_telegram_bot",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/l10n_bg_telegram_bot_views.xml",
        "views/l10n_bg_telegram_user_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
