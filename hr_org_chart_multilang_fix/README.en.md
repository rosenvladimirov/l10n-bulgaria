# HR Org Chart — Multilang Fix

> Resolve translatable JSONB employee names to plain strings before the hr_org_chart widget renders them.

**Module:** `hr_org_chart_multilang_fix` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Human Resources

## Overview

HR Org Chart — Multilang Fix
When ``hr.employee.name`` (or related Char fields) is made translatable by a
third-party module (e.g. ``l10n_bg_multilang`` + ``partner_multilang``), Odoo
18 stores the value as a PostgreSQL JSONB column
(``{"en_US": "...", "bg_BG": "..."}``).
The Enterprise ``hr_org_chart`` widget pulls employee data through the
``/hr/get_org_chart`` JSON-RPC route, whose ``_prepare_employee_data``
controller method serialises ``employee.name`` directly into the response
payload. Under certain request contexts (no active ``lang``, ``prefetch_langs``
flag, sudo without lang propagation, etc.), the field arrives at the
JavaScript layer as the raw JSONB dict, and the OWL template renders it as
``[object Object]``.
This patch module overrides ``_prepare_employee_data`` and resolves every
potentially translatable string field (``name``, ``job_name``, ``job_title``)

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `hr_org_chart` | — |

## Controllers

- `controllers/hr_org_chart.py`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'hr_org_chart_multilang_fix' or via CLI:
odoo -i hr_org_chart_multilang_fix -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
