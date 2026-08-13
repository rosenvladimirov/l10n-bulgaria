# 📝 Order Line Wording on the Delivery Slip

> Module: **l10n_bg_stock_sale_line_description** · Models: `stock.move` (field `sale_line_description`), inherited view `stock.view_picking_form`

## 📌 When to use
When a warehouse operator processes a delivery/picking and needs to see/print **the exact same wording** the salesperson entered on the sale order line — not just the product name.

## ✅ Before you start
- The `sale_stock` and `l10n_bg_stock_sale_line_description` modules must be installed.
- The wording must be entered by the salesperson on the **sale order** line, before the transfer is generated (or updated afterward — see "Common mistakes").

## 🧾 Step by step
1. Open the delivery transfer linked to a sale order.
2. In the **Operations** tab, next to each line you see an extra field with the description from the order (`sale_line_description`) — related, shown read-only.
3. When printing the **Accepted delivery report** (or the standard Delivery Slip), the lines table shows exactly that description instead of the bare product name.

## 📂 What gets generated
- Nothing new in the database — the field is **related, non-stored** (`stock.move.sale_line_description` = `sale_line_id.name`), computed live from existing data.

## ⚠️ Common mistakes
- Changing the order's description **after** the transfer has already been generated will still reflect automatically (the field is related, not a snapshot) — but double-check before printing if you've made corrections.
- Only transfers linked to a sale order line show the description — internal transfers without a `sale_line_id` keep the usual product display.

## 🔗 Related
For the overview of the two documents using this description, see *Accepted-Delivery Slip* and *Handover Protocol on the Sale Order* (Sales manual).
