# Bulgarian Invoice Copy

> Add COPY watermark to Bulgarian invoice reports

**Module:** `l10n_bg_invoice_copy` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Accounting/Localizations

## Overview

This module adds a "COPY" watermark to invoice reports in Bulgaria.
        It inherits the standard invoice report template and adds the copy designation.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `account` | `l10n_bg_report_theme` |

## Views

- `views/report_invoice_copy.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_invoice_copy' or via CLI:
odoo -i l10n_bg_invoice_copy -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
