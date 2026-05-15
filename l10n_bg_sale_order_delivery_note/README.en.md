# Bulgaria — Sale Order Accepted-Delivery Report

> A QWeb PDF "accepted delivery" / pro-forma report generated directly
> from a Bulgarian sale order.

**Module:** `l10n_bg_sale_order_delivery_note` | **Version:** 18.0.1.1.1 | **License:** LGPL-3 | **Category:** Localization

## Overview

Bulgarian sales practice often needs an accepted-delivery / pro-forma
document issued at the **sale-order** stage (before or instead of the
stock-side handover protocol). This module adds that report on
`sale.order`.

## What it provides

`ir.actions.report` `action_report_pro_forma_invoice` →
`report_saleorder_delivery_note` (qweb-pdf), bound to `sale.order` so
the document is available from the order's Print menu. Layout uses the
Bulgarian report theme.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `sale` | `l10n_bg`, `l10n_bg_report_theme` |

## Configuration

None. Install — the accepted-delivery report appears in the sale
order Print menu.

## Related modules

`l10n_bg_report_stock` provides the stock-picking-side handover
protocol + accepted-delivery slip; this module is the sale-order-side
counterpart.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Stock-side: `l10n_bg_report_stock`
