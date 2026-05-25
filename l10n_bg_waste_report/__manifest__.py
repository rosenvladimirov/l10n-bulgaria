# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Bulgaria - Waste Management (Reports)",
    "version": "19.0.1.0.0",
    "summary": "XLSX monthly report (Annex 4), annual report skeleton "
               "(Annex 18) and PDF identification document (Annex 8)",
    "description": """
Bulgaria Localization - Waste Management Reports
================================================

Regulatory reports for the Bulgarian waste management stack:

* **Annex 4** (Прил. №4 / Наредба №1/2014) — monthly bookkeeping XLSX
  with the four sections required by the regulation:

  1. Получен отпадък (received waste)
  2. Третиран отпадък (treated waste)
  3. Образуван отпадък (waste generated from treatment)
  4. Предаден отпадък (waste delivered out)

* **Annex 18** (Прил. №18) — annual summary XLSX (skeleton in v1, exposes
  yearly aggregates for manual submission via НИСО).

* **Annex 8** (Прил. №8) — hazardous-waste transport ID document PDF,
  rendered from the `l10n.bg.waste.id.document` record with the three
  regulatory sections (sender / carrier / receiver) and signature blocks.

XLSX reports use OCA `report_xlsx` from the `reporting-engine` repo.
""",
    "author": "Rosen Vladimirov, Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "category": "Localization/Bulgaria",
    "license": "AGPL-3",
    "depends": [
        "l10n_bg_waste_picking",
        "report_xlsx",
    ],
    "external_dependencies": {
        "python": ["xlsxwriter"],
    },
    "data": [
        "security/ir.model.access.csv",
        "wizards/waste_monthly_report_wizard_views.xml",
        "wizards/waste_annual_report_wizard_views.xml",
        "report/waste_monthly_report.xml",
        "report/waste_annual_report.xml",
        "report/waste_id_document_template.xml",
        "report/waste_id_document_report.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
