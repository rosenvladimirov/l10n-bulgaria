# Copyright 2026 BL Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Bulgaria — Invoice Original / Copy Stamp",
    "summary": "Adds a 'Гриф' field (ОРИГИНАЛ / КОПИЕ) to invoice reports",
    "version": "19.4.1.0.0",
    "category": "Accounting/Localizations",
    "website": "https://github.com/nichat-bg/l10n-bulgaria",
    "author": "Rosen Vladimirov, BL Consulting, Odoo Community Association (OCA)",
    "maintainers": ["rosen-vladimirov"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["account"],
    "data": [
        "views/report_invoice.xml",
    ],
}
