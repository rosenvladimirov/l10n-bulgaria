# Bulgaria - HR Holidays

> Bulgarian localization for HR Holidays

**Module:** `l10n_bg_hr_holidays` | **Version:** 18.0.1.4.0 | **License:** LGPL-3 | **Category:** Human Resources/Time Off

## Overview

Bulgarian Leave Types for Odoo
This module adds all official leave types for Bulgaria, including:
* 17 NHIF (NZOK) sick leave types (codes 01-17)
* 4 Annual paid leave types (Art. 155-157 Labor Code)
* 8 Civil and public duty leave types (Art. 157 Labor Code)
* 4 Special leave types (Art. 158-161 Labor Code)
* 7 Maternity and paternity leave types (Art. 163-168 Labor Code)
* 4 Educational leave types (Art. 169-171a Labor Code)
Total: 61 leave types
All leave types are compliant with:
* Bulgarian Labor Code (Кодекс на труда)
* NHIF Standards (НЗОК стандарти)
* Regulation on Working Time, Rest and Leave (НРВПО)
Features:

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `hr_contract`, `hr_holidays` | `l10n_bg` |

## New models

- `hr.leave.balance`
- `nssi.leave.reason`

## Extended models

- `hr.leave` (inherited)
- `hr.leave.allocation` (inherited)
- `hr.leave.type` (inherited)

## Views

- `views/hr_leave_balance_views.xml`
- `views/hr_leave_schedule_views.xml`
- `views/hr_leave_type_views.xml`
- `views/hr_leave_views.xml`
- `views/l10n_bg_nssi_leave_reason.xml`

## Seeded data

- `data/hr_holidays_data.xml`
- `data/hr_holidays_doo_treatment.xml`
- `data/nssi.leave.reason.csv`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_hr_holidays' or via CLI:
odoo -i l10n_bg_hr_holidays -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
