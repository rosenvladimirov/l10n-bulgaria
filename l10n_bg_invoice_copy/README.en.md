# Bulgaria — Invoice COPY Watermark

> Adds a "COPY" watermark to Bulgarian invoice reports so reprints are
> visually distinguishable from the original.

**Module:** `l10n_bg_invoice_copy` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Localization

## Overview

Bulgarian practice requires that any reprint of an already-issued
invoice is clearly marked as a copy ("КОПИЕ"), so it cannot be
mistaken for a second original. This module overlays a watermark on
the standard invoice PDF when the document is not the first print.

## What it does

Inherits the standard `account.report_invoice_document` QWeb template
and renders a diagonal "COPY" watermark layer over the invoice body.
Purely a report-layer change — no model fields, no data.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `account` | `l10n_bg` |

## Configuration

None. Install and the watermark appears on invoice reprints.

## Relationship to `l10n_bg_invoice_grif`

`l10n_bg_invoice_grif` is the richer variant — it adds an explicit
**Гриф** field (ОРИГИНАЛ / КОПИЕ) printed on the invoice. Use
`invoice_copy` for a simple visual watermark; use `invoice_grif` when
the original/copy status must be an explicit labelled field.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Sibling: `l10n_bg_invoice_grif`
