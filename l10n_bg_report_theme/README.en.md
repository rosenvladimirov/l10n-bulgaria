# Bulgaria - Report Theme Sections

> Professional report theme with modular section-based layout
            for Bulgarian business documents.

**Module:** `l10n_bg_report_theme` | **Version:** 18.0.5.2.0 | **License:** LGPL-3 | **Category:** ?

## Overview

Bulgaria - Report Theme Sections
This module provides a professional, customizable report theme specifically designed
for Bulgarian business documents, featuring a modular section-based layout system
with extensive customization options for headers, footers, backgrounds, and colors.
**Core Features**
-----------------
**Section-Based Layout Architecture**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Modular three-section design:
- **Header Section** - Company branding and contact information
- **Article Section** - Main document content area
- **Footer Section** - Page numbering and legal information
* Separate templates for portrait and landscape orientations
* Independent background images for each section

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `web`, `sale`, `account`, `stock`, `purchase` | `l10n_bg_config` |

**External Python packages:** `webcolors`

## Extended models

- `base.document.layout` (inherited)
- `ir.actions.report` (inherited)
- `res.company` (inherited)

## Views

- `views/base_document_layout_views.xml`
- `views/ir_action_report_templates.xml`
- `views/purchase_order_templates.xml`
- `views/purchase_quotation_templates.xml`
- `views/report_invoice.xml`
- `views/report_templates.xml`
- `views/res_company_views.xml`

## Seeded data

- `data/report_layout.xml`
- `data/report_paperformat_data.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_report_theme' or via CLI:
odoo -i l10n_bg_report_theme -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
