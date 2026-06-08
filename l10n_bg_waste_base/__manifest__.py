# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Bulgaria - Waste Management (Base)",
    "version": "19.4.1.0.0",
    "summary": "Bulgarian waste classification catalog, treatment activities, "
               "and treatment sites per Ordinance 2/2014 and the Waste Management Act",
    "description": """
Bulgaria Localization - Waste Management Base
=============================================

Foundation module of the Bulgarian waste management stack. Provides the
master data and reusable mixins used by every downstream waste module
(permit, picking, report). Implements the regulatory model defined by
Ordinance 2/2014 (waste classification) and the Waste Management Act.

**Core Features**
-----------------

* Waste code catalog (Ordinance 2/2014, Annex 1 - 20 sections, 840+ codes)
  with hierarchy, hazardous flag and mirror-code relationships (Art. 10).
* R/D treatment activity catalog (R1-R13 recovery, D1-D15 disposal) per
  the Annexes 1 and 2 of the supplementary provisions of the Waste
  Management Act.
* Treatment site model - physical location where a permit is exercised;
  binds to stock warehouses for downstream picking flows.
* res.partner extension flagging waste operators and their permits.
* res.company extension exposing the company-level waste manager (the
  responsible user receiving over-quota notifications).
* Three-tier security model: User / Manager / Admin.

**Companion Modules**
---------------------

* `l10n_bg_waste_permit`  — permits and quotas with online usage compute
* `l10n_bg_waste_picking` — stock.picking, move.line, lot integration
* `l10n_bg_waste_report`  — Annex 4 (monthly) and Annex 18 (annual) XLSX
""",
    "author": "Rosen Vladimirov, Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "category": "Localization/Bulgaria",
    "license": "AGPL-3",
    "depends": [
        "base",
        "stock",
        "mail",
        "l10n_bg_config",
    ],
    "data": [
        "security/waste_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/waste_activity_data.xml",
        "data/waste_code_data.xml",
        "views/waste_code_views.xml",
        "views/waste_activity_views.xml",
        "views/waste_site_views.xml",
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
        "views/menu_views.xml",
    ],
    "demo": [],
    "installable": True,
    "application": True,
    "images": [
        "static/description/icon.png",
    ],
}
