# 🚢 Importing from Outside the EU

> Models: `purchase.order`, `stock_landed_costs` · Result at billing: **Outside EU** fiscal position + customs declaration

## 📌 When to use
When the vendor is from a country outside the European Union and the goods go through customs clearance (import under Art. 16 of the VAT Act). The customs value and additional costs (freight, insurance, duties) determine the base for import VAT.

## ✅ Before you start
- The vendor must have a **country outside the EU**.
- Know/have available the vendor's **EORI number** (see *Supplier EORI Number*).
- The `stock_landed_costs` module, if additional import costs (freight, insurance, duties) need to be allocated onto the goods' cost.

## 🧾 Step by step
1. Create the purchase order to the non-EU vendor normally.
2. Receive the goods (`stock.picking`) — usually after customs clearance.
3. If there are additional import costs (freight, insurance, duties) — record them via **Landed Costs** and allocate them onto the received goods to get an accurate cost.
4. Create the vendor bill — the **Outside EU** fiscal position should apply automatically.
5. On the bill, fill in the customs declaration data — customs value (`l10n_bg_customs_value`), gross/net weight (`l10n_bg_weight_gross`/`l10n_bg_weight_net`) and customs procedure (`customs_procedure`) on the lines, if not auto-filled.
6. Confirm the bill — a customs declaration (`account.move.bg.customs`) is generated with the VAT due on the customs value.

## 📂 What gets generated
- At the order/receipt level — a standard Odoo transfer, no Bulgaria-specific documents.
- At the bill level — a customs declaration with VAT calculated on the customs value plus accumulated costs.

## ⚠️ Common mistakes
- Skipping the landed costs allocation → the goods' cost stays understated (missing freight/duties).
- Missing customs value on the bill line → the declaration cannot be calculated correctly.
- Confusing an import from a third country (Art. 16, this article) with an intra-community acquisition from the EU (Art. 84, see *Buying from an EU Supplier*) — different rules and different protocols/declarations.

## 🔗 Related
The full step-by-step scenario on the bill — *Outside EU — Purchase (Import)* in the VAT administration manual (`l10n_bg_tax_admin_manual`).
