# Bulgaria — Picking Comment-Template Positioning

> Repositions the `base_comment_template` top/bottom blocks on the
> Bulgarian handover protocol and accepted-delivery slip so the
> commercial text lands where the BG document layout expects it.

**Module:** `l10n_bg_stock_picking_comment_template` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Localization

## Overview

OCA's `base_comment_template` injects standard top/bottom commercial
text into reports, but its default anchor points don't match the
Bulgarian handover-protocol / accepted-delivery layout from
`l10n_bg_report_stock`. This module re-anchors those comment blocks to
the correct positions on the BG documents.

## What it does

Inherits `stock.report_delivery_document`:

- `<xpath expr="//div[@id='informations']" position="after">` — top
  comment block placed after the info block
- `<xpath expr="//div[@name='signature']" position="before">` — bottom
  comment block placed before the signature area

Layout-aware via guards (`is_handover_protocol`,
`l10n_bg_report_stock_accepted`) so it only repositions on the
relevant BG documents, not on the generic delivery slip.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `stock`, `base_comment_template` | `l10n_bg`, `l10n_bg_report_stock` |

## Configuration

None. Install alongside `l10n_bg_report_stock` and
`base_comment_template`; comment blocks render in the correct place
on the BG handover/accepted-delivery documents.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Documents: `l10n_bg_report_stock`
