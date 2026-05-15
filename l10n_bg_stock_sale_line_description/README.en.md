# Bulgaria — Sale Line Description on Pickings

> Shows the sale-order line description on stock pickings and delivery
> slips, so the delivered item text matches what the customer ordered.

**Module:** `l10n_bg_stock_sale_line_description` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Localization

## Overview

By default a delivery slip shows the product name, not the descriptive
text the salesperson entered on the sale-order line. Bulgarian
customers expect the delivery document to carry the same wording as
the order. This module surfaces the SO line description on the picking
form and the delivery-slip report.

## What it does

- Inherits `stock.view_picking_form` — adds the SO line description
  next to `description_picking` in the operations page.
- Inherits `stock.report_delivery_document` (and the serial-move-line
  variant) — prints the description in the move table.

Report/view-layer only — no model fields.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `sale_stock` | `l10n_bg` |

## Configuration

None. Install — the description follows from the sale order onto the
picking and its printed delivery slip.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Related: `l10n_bg_report_stock`, `l10n_bg_stock_picking_comment_template`
