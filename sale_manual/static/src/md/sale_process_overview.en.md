# 🛍️ Sales Process Overview

> App: **Sales** (`sale`) · Models: `sale.order`, `sale.order.line`

## 📌 When to use
Whenever you need to quote a customer, confirm the quotation as an order, and track its delivery and invoicing. This is the core workflow of the app, before any Bulgaria-specific documents come into play.

## ✅ Before you start
- The customer (`res.partner`) must exist with correct data — country, VAT/company ID (if a company), delivery address and invoicing address.
- Products must have a sales price and a default tax set.
- If the company manages a warehouse — the `sale_stock` module (usually installed together with Sales + Inventory).

## 🧾 Step by step
1. **Sales → Orders → New**.
2. Pick a **Customer** — the fiscal position and currency load automatically from their record.
3. Add lines with products, quantity and price. Discounts and pricelists apply at the line level.
4. Check **Payment Terms** and **Delivery Date**.
5. **Send** the quotation to the customer (by email or printed) or go straight to **Confirm** if already agreed.
6. Once confirmed, the order automatically generates a **delivery transfer** (if a warehouse is linked) and is ready to be **invoiced**.
7. **Create invoice** — in full or partially, depending on the invoicing policy of the products (ordered quantity vs. delivered quantity).

## 📂 What gets generated
- A confirmed sale order (`sale.order`, state `sale`).
- A delivery transfer (`stock.picking`), if products are tracked in stock.
- A customer invoice (`account.move`), linked back to the order.

## ⚠️ Common mistakes
- Missing/wrong fiscal position on the customer → wrong VAT on the invoice. Check it before confirming, especially for EU or non-EU customers.
- Mixing "ordered quantities" invoicing policy with partial deliveries — causes confusion at invoicing time.
- Missing delivery address for customers with multiple sites.

## 🔗 Related
For printing the handover protocol on delivery — see *Handover Protocol*. For the wording of items on the transport document — see *Order Line Wording on the Delivery Slip*.
