# 🛒 Purchase Process Overview

> App: **Purchase** (`purchase`) · Models: `purchase.order`, `purchase.order.line`

## 📌 When to use
Whenever you need to request a quotation from a vendor (RFQ), confirm it as a purchase order, receive the goods, and finally post the vendor's invoice.

> ⚠️ **Important**: no Bulgarian localization module adds fields or logic to `purchase.order`/`purchase.order.line`. All VAT/customs handling (Art. 117 protocols, customs declarations, reverse charge) happens **on the vendor bill**, not on the purchase order. See *From Purchase Order to Vendor Bill — Fiscal Bridge*.

## ✅ Before you start
- The vendor (`res.partner`) must exist with a correct country and VAT number.
- Products must have a cost/vendor price set (if a vendor pricelist is used).
- The `purchase_stock` module, if goods are physically received into a warehouse.

## 🧾 Step by step
1. **Purchase → Requests for Quotation → New**.
2. Pick a **Vendor** and add products with expected quantities/prices.
3. Send the RFQ to the vendor, or go straight to **Confirm Order**.
4. When goods arrive — process the receipt transfer (`stock.picking`) from the order's **Receive Products** button.
5. Create the **Vendor Bill** — from the order's button (billed on ordered or received quantities, depending on the billing policy setting).
6. From this point on, the bill (not the order) carries all the VAT/protocol logic.

## 📂 What gets generated
- A confirmed purchase order (`purchase.order`, state `purchase`).
- A receipt transfer (`stock.picking`), if products are tracked in stock.
- A vendor bill (`account.move`, type `in_invoice`), linked back to the order.

## ⚠️ Common mistakes
- Expecting the order to "know" the vendor's fiscal position — it's only determined at the bill stage, not on the order.
- Mismatch between received and billed quantity on partial deliveries.
- Missing vendor VAT number/EORI — doesn't block the order itself, but will complicate billing later.

## 🔗 Related
For the link between the order and the bill's VAT treatment — see *From Purchase Order to Vendor Bill — Fiscal Bridge*.
