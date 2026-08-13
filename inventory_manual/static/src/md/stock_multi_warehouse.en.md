# 🏭 Multiple Warehouses and Locations

> Models: `stock.warehouse`, `stock.location` · Standard Odoo functionality, practical guidance

## 📌 When to use
When the company operates more than one physical warehouse/site (e.g. central warehouse + retail locations, or a warehouse plus a consignment stock at a customer's site) and stock needs to be tracked separately per location.

## ✅ Before you start
- Enable **Multiple Warehouses** from Inventory → Settings.
- Decide on the structure: a separate warehouse per branch, or one warehouse with several internal locations (shelves/zones) — the choice depends on the need for per-site reporting.

## 🧾 Step by step
1. **Inventory → Configuration → Warehouses → New**.
2. Set a short code (e.g. `CW` for central warehouse, `RT1` for retail site 1) — used in transfer numbering.
3. Check the automatically generated locations (Stock, Input, Output) for the new warehouse.
4. If needed, add extra internal locations (zones, shelves) under the main "Stock" location.
5. When creating a purchase/sale order — pick the correct warehouse in the **Warehouse** field so movements land in the right locations.
6. Use internal transfers to move goods between warehouses/locations as needed.

## 📂 What gets generated
- Separate stock levels (`stock.quant`) per location — allows an accurate view of "what is where".
- Separate transfer numbering per warehouse (e.g. `CW/PICK/00001`, `RT1/PICK/00001`).

## ⚠️ Common mistakes
- Forgetting a user's default warehouse is wrong → transfers ending up in the wrong warehouse.
- An overly complex location structure without a real need — complicates daily work without benefit.
- Missing a route between warehouses when automatic replenishment is needed — check per-warehouse reordering rules.

## 🔗 Related
For the core transfer process, see *Warehouse Process Overview*.
