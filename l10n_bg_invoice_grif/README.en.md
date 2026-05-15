# Bulgaria — Invoice Гриф (ОРИГИНАЛ / КОПИЕ)

> Adds an explicit "Гриф" field (ОРИГИНАЛ / КОПИЕ) printed on the
> Bulgarian invoice — the labelled-field counterpart to the plain
> watermark in `l10n_bg_invoice_copy`.

**Module:** `l10n_bg_invoice_grif` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Localization

## Overview

Bulgarian accounting practice distinguishes the **original** of an
invoice from any **copy** with an explicit "Гриф" annotation, not just
a visual mark. This module inherits the invoice QWeb template and
prints the Гриф value (ОРИГИНАЛ / КОПИЕ) in the document's
information block.

## What it does

Inherits `account.report_invoice_document`:

- `<xpath expr="//t[@t-set='o']" position="after">` sets up the
  context for the grif value.
- `<xpath expr="//div[@id='informations']" position="inside">` prints
  the Гриф label inside the standard invoice info block.

Report-layer only — no stored model fields beyond what drives the
original/copy determination.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `account` | `l10n_bg` |

## Configuration

None. Install — the Гриф appears in the invoice info block;
first print = ОРИГИНАЛ, subsequent = КОПИЕ.

## Relationship to `l10n_bg_invoice_copy`

`invoice_copy` overlays a diagonal "COPY" watermark; `invoice_grif`
adds an explicit labelled Гриф field. Pick by whether you need a
visual mark or an explicit annotation; they can also be combined.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Sibling: `l10n_bg_invoice_copy`
