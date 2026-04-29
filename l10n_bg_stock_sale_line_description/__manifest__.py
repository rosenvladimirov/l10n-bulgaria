# Copyright 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Stock Sale Line Description",
    "summary": "Show sale order line description on pickings and delivery slips",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "author": "Rosen Vladimirov",
    "depends": [
        "stock",
        "sale_stock",
    ],
    "data": [
        "security/res_groups.xml",
        "views/stock_picking_views.xml",
        "report/report_deliveryslip.xml",
    ],
    "demo": [],
    "tags": ["stock", "sale", "reports"],
    "odoo_version": "19.0",
    "python_version": ">=3.12",
}
