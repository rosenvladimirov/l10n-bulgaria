# Bulgaria - NRA API Integration

> Core module for submitting declarations to the Bulgarian National Revenue Agency (НАП) via public API

**Module:** `l10n_bg_api_nra` | **Version:** 18.0.1.4.2 | **License:** LGPL-3 | **Category:** Accounting/Localizations/Bulgaria

## Overview

Bulgaria - NRA API Integration
Core module providing infrastructure for automated submission of declarations
to the Bulgarian National Revenue Agency (НАП) through their public REST API
at https://public-api.nra.bg/.
Core Features
-------------
* OAuth 2.0 authentication with NRA API (client credentials grant)
* Rate limiting handling (token bucket: 15 burst, 5/s replenish)
* Base declaration model with full workflow (draft → submitted → accepted/rejected)
* XML payload generation and XSD validation framework
* Submission status tracking with NRA document/incoming numbers
Supported Declaration Types
----------------------------
* **Декларация обр. 1** — Data for insured persons (Данни за осигурените лица)

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `mail`, `hr` | `l10n_bg_config`, `l10n_bg_bank_wallet` |

**External Python packages:** `requests`, `lxml`

## New models

- `nra.api.provider`
- `nra.declaration`
- `nra.declaration.d1.line`
- `nra.declaration.d6.line`
- `nra.declaration.h18.line`
- `nra.declaration.h18.line.art`
- `nra.declaration.h18.refund`
- `nra.declaration.vat.line`
- `nra.declaration.vies.line`

## Extended models

- `hr.employee` (inherited)
- `nra.declaration` (inherited)
- `res.company` (inherited)
- `res.users` (inherited)

## Views

- `views/hr_employee_views.xml`
- `views/menu.xml`
- `views/nra_declaration_h18_views.xml`
- `views/nra_declaration_views.xml`
- `views/res_company_views.xml`

## Controllers

- `controllers/main.py`

## Seeded data

- `data/nra_data.xml`
- `data/xsd`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_api_nra' or via CLI:
odoo -i l10n_bg_api_nra -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
