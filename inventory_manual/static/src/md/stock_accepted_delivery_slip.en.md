# 📄 Accepted-Delivery Slip

> Module: **l10n_bg_report_stock** · Model: `stock.picking` · Report: **Accepted delivery report**

## 📌 When to use
When you need to print a representative document for the accepted/delivered goods directly from the warehouse transfer (receipt or delivery) — without going through the invoice.

## ✅ Before you start
- The `l10n_bg_report_stock` module must be installed.
- The transfer (`stock.picking`) must exist with lines filled in.

## 🧾 Step by step
1. Open the transfer (receipt, delivery, or internal transfer).
2. From the **Print** menu, select **Accepted delivery report**.
3. The report shows the partner, product lines and quantities, styled with the shared Bulgarian theme.
4. If the `l10n_bg_stock_sale_line_description` module is installed — lines show the description from the order, not just the product name (see *Order Line Wording on the Delivery Slip*).

## 📂 What gets generated
- A PDF document named **"Accepted delivery report - <partner> - <transfer number>"**.
- No accounting entry is created.

## ⚠️ Common mistakes
- Don't confuse this with the **Accepted delivery report** at the `sale.order` level (module `l10n_bg_sale_order_delivery_note`) — it's the SAME report name, but at TWO different levels (order vs. transfer) provided by two separate modules. Check where you're printing from (the order or the transfer).

## 🔗 Related
The analogous document at the sale order level — *Handover Protocol on the Sale Order* in the Sales manual.
