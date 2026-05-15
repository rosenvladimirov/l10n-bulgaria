# Multi Language Partner, Company, Employee

**Module:** `l10n_bg_multilang` | **Version:** 18.0.0.1.0 | **License:** LGPL-3 | **Category:** Localization

## Overview

Multi language support for Partner, Company, Employee.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `hr`, `stock`, `partner_multilang` | `partner_multilang` |

## New models

- `hr.employee`
- `res.country.state`

## Extended models

- `res.bank` (inherited)
- `res.currency` (inherited)
- `resource.resource` (inherited)
- `stock.warehouse` (inherited)

## Views

- `views/res_country_view.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_multilang' or via CLI:
odoo -i l10n_bg_multilang -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
