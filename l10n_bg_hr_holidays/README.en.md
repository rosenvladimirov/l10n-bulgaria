# Bulgaria — HR Holidays (61 Labor-Code leave types)

> The full Bulgarian leave-type catalogue per the Labor Code (КТ) and
> NHIF (НЗОК): annual paid leave, sick leave, maternity/paternity,
> educational, civic-duty — with NSSI reason codes, DOO treatment,
> pro-rata allocation and an annual-schedule planner.

**Module:** `l10n_bg_hr_holidays` | **Version:** 18.0.1.4.0 | **License:** LGPL-3 | **Category:** Human Resources/Time Off

## Overview

Odoo ships a generic time-off model; Bulgarian payroll needs the
**61 statutory leave types** with their legal codes, the 17 NHIF
sick-leave reason codes, and the social-security treatment each type
gets (does a day reduce the DOO base? is it employer-paid?). This
module supplies all of that as the data + model layer the payroll
modules consume.

## Data model

### `hr.leave.type` (extended)

| Field | Purpose |
|---|---|
| `l10n_bg_code` | Statutory code, e.g. `155` (paid annual, КТ art. 155-157), `163` (maternity). Drives display name `[code] name` and downstream filtering |
| `l10n_bg_allow_paid_days` | Marks types where employer-paid days apply |
| `l10n_bg_leave_reason_id` | M2O → `nssi.leave.reason` |
| `l10n_bg_doo_treatment` | Selection — how the leave affects the DOO insurance base (NSSI-funded vs base-excluded vs normal). Set for maternity types KT163/163-10/164/166 (Phase 1 #1.3) |

### `nssi.leave.reason` (new)

The 17 NHIF/НЗОК sick-leave reason codes (`code` + `name`),
seeded from `data/nssi.leave.reason.csv`. Used to classify sick
leaves for NSSI certificate generation.

### `hr.leave.balance` (new — SQL view)

Read-only `_auto=False` view: per `employee_id` × `leave_type_id`
the allocated / taken / remaining days. Powers balance widgets
without recomputing on every read.

### `hr.leave` (extended)

`l10n_bg_leave_reason_id` + `l10n_bg_show_paid_days_fields` — surface
the reason code and employer-paid-day inputs on the leave request.

### `hr.leave.allocation` (extended — Phase 5.2)

`l10n_bg_compute_pro_rata_days(...)` + `_l10n_bg_count_pro_rata_months`
— pro-rata annual-leave entitlement when an employee joins/leaves
mid-year (half-month rounding rule).

## Seeded data

- `data/hr_holidays_data.xml` — the 61 leave types: 4 paid-annual
  (КТ 155-157), 8 civic/public-duty (КТ 157), 4 special (КТ 158-161),
  7 maternity/paternity (КТ 163-168), 4 educational (КТ 169-171a),
  + 17 NHIF sick-leave types (codes 01-17).
- `data/hr_holidays_doo_treatment.xml` — DOO-treatment flags
  (Phase 1 #1.3 maternity handling).
- `data/nssi.leave.reason.csv` — NHIF reason codes.

## Views

- Leave type / leave request extensions (code + reason + paid days)
- `hr_leave_balance_views.xml` — balance pivot/list
- **`hr_leave_schedule_views.xml`** — Annual Leave Schedule (Phase 5.1):
  year-mode calendar coloured by employee + pivot (employee × month) +
  paid-annual-leave search filter; menu under Time Off → Reports.

## Relationship to payroll

`l10n_bg_hr_payroll_holidays` (EE) builds on this: auto-creates NSSI
sick certificates on approval and adds the **чл. 37а НРВПО**
notification (Phase 2.4) for leaves over 30 working days. The DOO
treatment set here feeds the maternity DOO-base reduction in
`l10n_bg_hr_payroll`.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `hr_contract`, `hr_holidays` | `l10n_bg` |

## Configuration

1. Install → 61 leave types + NHIF reason codes load automatically.
2. HR → Configuration → Time Off Types: review codes/DOO treatment.
3. Create allocations for annual-leave types; use the pro-rata helper
   for mid-year joiners.
4. Time Off → Reports → Annual Leave Schedule for the planning view.

## Known limitations

- `hr.leave.balance` is a read-only SQL view (no write-back).
- Pro-rata helper applies the standard half-month rule; non-standard
  contractual schemes need manual allocation.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Payroll consumer: `l10n-bulgaria-ee/l10n_bg_hr_payroll_holidays`
- Roadmap: `claude.ai/memory/project_payroll_personnel_roadmap_2026_05_13.md`
- `data/hr_leave_types_documentation_bg.md` — per-type legal reference
