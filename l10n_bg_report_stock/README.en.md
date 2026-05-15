# Bulgaria — Stock Handover & Accepted-Delivery Documents

> Adds the Bulgarian accepted-delivery slip and handover protocol
> (приемно-предавателен протокол) PDF reports to stock pickings.

**Module:** `l10n_bg_report_stock` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Localization

## Overview

Bulgarian goods movements are documented with a **приемно-предавателен
протокол** (handover protocol) and an **accepted-delivery slip** —
signed proof of delivery/acceptance distinct from the invoice. This
module adds those two PDF reports to `stock.picking` using the
section-based `l10n_bg_report_theme` layout.

## What it provides

- `report/report_accepted_deliveryslip.xml` — accepted-delivery slip
- `report/report_handover_protocol.xml` — handover protocol
- `report/stock_report_views.xml` — wires the reports to the picking
- `stock.move.line._get_aggregated_product_quantities()` extended so
  the documents aggregate quantities the Bulgarian way

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `stock` | `l10n_bg`, `l10n_bg_report_theme` |

## Configuration

None. Install — the two reports appear in the Print menu of stock
pickings.

## Related modules

- `l10n_bg_stock_picking_comment_template` — repositions
  base_comment_template blocks on these documents
- `l10n_bg_stock_sale_line_description` — adds SO line description
- `l10n_bg_sale_order_delivery_note` — SO-side accepted-delivery report

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Report theme: `l10n_bg_report_theme`
