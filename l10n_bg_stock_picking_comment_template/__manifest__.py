# Copyright 2026 BL Consulting
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Bulgaria — Stock Picking Comment Template Positioning",
    "summary": "Render base_comment_template top/bottom blocks on the "
               "Bulgarian accepted delivery slip report",
    "version": "19.0.1.0.0",
    "category": "Warehouse Management",
    "license": "AGPL-3",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd., "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "maintainers": ["rosenvladimirov"],
    "depends": [
        "l10n_bg_report_stock",
        "stock_picking_comment_template",
    ],
    "data": [
        "views/report_stock_picking_comments.xml",
    ],
    "installable": True,
    "application": False,
}
