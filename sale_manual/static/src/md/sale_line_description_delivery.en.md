# 📝 Order Line Wording on the Delivery Slip

> Module: **l10n_bg_stock_sale_line_description** · Models: `sale.order.line`, `stock.move`

## 📌 When to use
By default the delivery slip shows the **product name**, not the descriptive text the salesperson entered on the order line. Bulgarian customers usually expect the delivery document to carry **the same wording** as the quotation/order (e.g. color, size, batch, or contract-specific notes). This module fixes exactly that mismatch.

## ✅ Before you start
- The `sale_stock` and `l10n_bg_stock_sale_line_description` modules must be installed.
- No configuration is required — it works automatically once installed.

## 🧾 Step by step
1. On the sale order line, edit/extend the **description** (the field below the product name) the way you want it to appear to the customer.
2. Confirm the order — a delivery transfer (`stock.picking`) is generated.
3. On the picking form, in the **Operations** tab, next to each line you see the description carried over from the order (`sale_line_description`), not just the standard `description_picking`.
4. When printing the **Delivery Slip** report, the lines table shows exactly that description.

## 📂 What gets generated
- No new field is stored in the database — `sale_line_description` is a **related, non-stored** field (`stock.move.sale_line_description`, computed from `sale_line_id.name`).
- Only the picking form's view and the printed Delivery Slip report change — the data already exists on the order.

## ⚠️ Common mistakes
- If the order line description is empty/just the product name, the slip will look the same as before — the module doesn't add text, it only carries it over.
- Only applies to transfers linked to a `sale.order.line` (i.e. coming from a sale) — internal transfers with no order link are unaffected.

## 🔗 Related
For the handover protocol at the delivery level, see *Handover Protocol* in the Inventory manual — the two modules are often used together.
