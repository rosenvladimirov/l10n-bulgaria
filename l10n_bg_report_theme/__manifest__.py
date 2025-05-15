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
        "l10n_bg_config",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/report_templates.xml",
        "data/report_layout.xml",
        "data/report_paperformat_data.xml",
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
            "l10n_bg_report_theme/static/src/webclient/actions/sffont.scss",
            "l10n_bg_report_theme/static/src/webclient/actions/reports/report_variable_colors.scss",
            "l10n_bg_report_theme/static/src/webclient/actions/reports/report_variable_fonts.scss",
            "l10n_bg_report_theme/static/src/webclient/actions/reports/layout_assets/layout_background.scss",
            "l10n_bg_report_theme/static/src/webclient/actions/reports/layout_assets/layout_sections.scss"
        ],
    },
}
