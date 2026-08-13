# 📦 Warehouse Process Overview

> App: **Inventory** (`stock`) · Models: `stock.picking`, `stock.move`, `stock.move.line`

## 📌 When to use
Whenever goods come in (receipt), go out (delivery), or move between locations/warehouses within the company (internal transfer).

## ✅ Before you start
- The warehouse (`stock.warehouse`) and locations must be configured.
- Products must be marked as stock-tracked (`type = 'product'`, "Track Inventory").
- If working with lots/serial numbers — set the relevant tracking policy on the product.

## 🧾 Step by step
1. **Inventory → Operations** — here you see all transfers: receipts, deliveries, internal transfers.
2. On receipt from a vendor — the transfer is generated automatically from a confirmed purchase order (or created manually).
3. On delivery to a customer — the transfer is generated automatically from a confirmed sale order.
4. Open the transfer, check/adjust the actual quantities on the lines (`stock.move.line`).
5. Click **Validate** — the goods are officially moved between locations, stock levels are updated.
6. If needed, print the relevant document (delivery slip, handover protocol — see the following articles).

## 📂 What gets generated
- `stock.move`/`stock.move.line` records — quantity movement between locations.
- Updated stock levels (`stock.quant`) for the products in the affected locations.

## ⚠️ Common mistakes
- Validating a transfer with a wrong quantity entered — fix it **before** Validate, afterward a correction requires a new transfer.
- Missing default location for a new warehouse — causes errors when creating transfers.
- Mismatched lots/serial numbers for a product requiring tracking.

## 🔗 Related
For printing the Bulgarian delivery documents, see *Handover Protocol* and *Accepted-Delivery Slip*.
