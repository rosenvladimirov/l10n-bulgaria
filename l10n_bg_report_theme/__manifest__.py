# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Report Theme Sections",
    "summary": """
        Report theme separate on sections.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "depends": [
        "web",
        "sale",
        "account",
        "stock",
        "purchase",
    ],
    "data": [
        "views/report_templates.xml",
        "data/report_layout.xml",
        "views/res_company_views.xml",
        "views/base_document_layout_views.xml",
        "views/ir_action_report_templates.xml",
        "views/report_invoice.xml",
        "views/purchase_order_templates.xml",
        "views/purchase_quotation_templates.xml",
    ],
    "demo": [],
    "assets": {
        "web.report_assets_common": [
            "report_theme_sections/static/src/webclient/actions/sffont.scss",
            "report_theme_sections/static/src/webclient/actions/reports/report.scss",
            "report_theme_sections/static/src/webclient/actions/reports/layout_assets/layout_sections.scss",
            "report_theme_sections/static/src/webclient/actions/reports/layout_assets/layout_background.scss",
        ]
    },
}
