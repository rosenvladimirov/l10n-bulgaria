# Bulgarian HR Payroll Classifications

> Bulgarian localization for HR payroll with NKPD and Economic Activity classifications

**Module:** `l10n_bg_payroll_classifications` | **Version:** 18.0.5.0.1 | **License:** LGPL-3 | **Category:** Human Resources/Localization

## Overview

Bulgarian HR Payroll Classifications
    ====================================
    This module provides Bulgarian localization for HR and payroll management with:
    Key Features:
    -------------
    * NCOP (National Classification of Occupations and Positions) management
    * Economic Activities (KID) classification with MOD rates
    * Bulgarian-specific HR menus structure
    * Integration with standard HR modules
    NCOP Classifications:
    ---------------------
    * Complete NCOP hierarchy management (НКПД 2011)
    * Professional groups and categories
    * Integration with employee positions

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `hr` | — |

## New models

- `bg.hr.payroll.economic.activity`
- `bg.hr.payroll.ncop.classification`

## Extended models

- `hr.job` (inherited)

## Views

- `views/bg_mod_economic_activity.xml`
- `views/bg_ncop_classification.xml`
- `views/hr_job_views.xml`
- `views/hr_menus.xml`

## Seeded data

- `data/bg_hr_payroll_economic_activity`
- `data/bg_hr_payroll_ncop_classification`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_payroll_classifications' or via CLI:
odoo -i l10n_bg_payroll_classifications -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
