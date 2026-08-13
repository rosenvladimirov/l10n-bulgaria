# 🌍 Selling to EU and Non-EU Customers

> Models: `sale.order`, `res.partner`, `account.fiscal.position`

## 📌 When to use
Any time the customer is not established in Bulgaria. The sale order itself **contains no** Bulgarian VAT logic — it is determined by the **fiscal position** set on the customer and/or applied automatically when the invoice is confirmed. This article explains what a salesperson should check at the order level before it reaches invoicing.

## ✅ Before you start
- The customer must have a **Country** set.
- For EU company customers — a valid **VAT number** (verifiable in VIES).
- For non-EU customers — an **EORI number** if customs procedures are involved.

## 🧾 Step by step
1. When creating/editing the customer — fill in **Country** and **VAT No.** correctly. This determines which fiscal position applies.
2. On the order, check the **Fiscal Position** field (Other Info) — expect one of:
   - **Domestic** — a Bulgarian customer;
   - **EU B2B** — an EU company with a valid VAT number (Intra-Community Supply, Art. 7);
   - **EU B2C** — an EU private individual (distance sales / OSS scheme);
   - **Outside EU** — a non-EU customer (export, Art. 28).
3. If the fiscal position looks wrong — check the customer's country and VAT number; set the position manually if needed.
4. Confirm the order and proceed to delivery/invoicing as usual.
5. The actual **VAT handling** (zero rate, VIES reporting, export evidence) happens when the **invoice** is created — see the corresponding scenario in the VAT administration manual.

## 📂 What gets generated
- The order carries the selected fiscal position over to the invoice, but the actual VAT logic (rate, protocol, VIES) is applied at the `account.move` level, not on the `sale.order`.

## ⚠️ Common mistakes
- An EU company customer without a valid VAT number → the system may apply **EU B2C** instead of **EU B2B**, which changes the VAT treatment. Verify the number in VIES before confirming.
- A delivery address different from the customer's address (e.g. delivery to a warehouse in another country) may require a different fiscal position than the default one.
- Remember that **the order itself does not verify** the VAT number — that's the salesperson's responsibility before confirming.

## 🔗 Related
For the full VAT logic at invoicing — see the *Guide to VAT Administration (Bulgaria)* manual (`l10n_bg_tax_admin_manual` module), scenarios *EU B2B — Sale*, *EU B2C — Sale*, *Outside EU — Sale (Export)*.
