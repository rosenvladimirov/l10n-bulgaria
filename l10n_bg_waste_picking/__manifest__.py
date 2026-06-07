# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Bulgaria - Waste Management (Stock Picking Integration)",
    "version": "20.0.1.0.0",
    "summary": "Capture waste codes at stock.picking validation, enforce "
               "permit quota and trace lots back to incoming pickings",
    "description": """
Bulgaria Localization - Waste Stock Picking Integration
=======================================================

Wires the waste compliance model into the standard Odoo stock flow:

* **`stock.picking`** — flags waste pickings, hooks `button_validate()` to
  open a wizard when a waste code is missing on a move line, and gates
  validation when a treatment quota is exceeded.
* **`stock.move.line`** — adds `waste_code_id`, `waste_quantity_kg`
  (auto-converted to kg from the line's UoM) and `waste_origin_partner_id`
  used by Annex 4 / 18 reports.
* **`stock.lot`** — links each lot back to the incoming pickings it
  originated from, enabling traceability of recycled output back to the
  source waste shipment.
* **`stock.picking.type`** — `waste_default_activity_id` to preset the R/D
  activity for incoming-waste picking types.
* **`product.template`** — `is_waste_product` flag.

**Wizard**
~~~~~~~~~~

`l10n.bg.waste.code.wizard` opens when a user clicks *Validate* on an
incoming picking that has waste lines lacking a code. The wizard requires
the user to:

1. Set a code per move line.
2. If the resulting quantity would breach 80% / 100% of the active quota,
   provide an explicit confirmation and a justification note that is
   then logged in the picking chatter.

**Identification document (Annex 8 of Наредба №1/2014)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`l10n.bg.waste.id.document` — mandatory for hazardous waste transport.
Captures the three sections (sender / carrier / receiver) and links to
the underlying picking. PDF rendering is shipped by the companion
`l10n_bg_waste_report` module.
""",
    "author": "Rosen Vladimirov, Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "category": "Localization/Bulgaria",
    "license": "AGPL-3",
    "depends": [
        "l10n_bg_waste_permit",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "wizards/waste_code_wizard_views.xml",
        "views/product_template_views.xml",
        "views/stock_picking_type_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_move_line_views.xml",
        "views/stock_lot_views.xml",
        "views/waste_id_document_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
