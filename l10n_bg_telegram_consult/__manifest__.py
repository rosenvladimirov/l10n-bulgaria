# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Telegram Bot: Consultations",
    "version": "19.0.1.4.0",
    "category": "Services",
    "summary": "Consultation requests from Telegram on prepaid hours, human-approved",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd., "
    "Odoo Community Association (OCA)",
    "maintainers": ["rosen-vladimirov"],
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria/tree/19.0/"
    "l10n_bg_telegram_consult",
    "license": "LGPL-3",
    "depends": ["l10n_bg_telegram_bot_sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ir_cron_data.xml",
        "views/l10n_bg_telegram_consult_request_views.xml",
        "views/l10n_bg_telegram_bot_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
