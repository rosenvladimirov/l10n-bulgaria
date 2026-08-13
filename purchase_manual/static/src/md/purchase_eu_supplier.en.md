# 🇪🇺 Buying from an EU Supplier

> Models: `purchase.order`, `res.partner` · Result at billing: **EU B2B** fiscal position

## 📌 When to use
When the vendor is a VAT-registered company from another EU member state. The goods/service will be treated as an **intra-community acquisition** (Art. 84 of the VAT Act) at billing time — with an automatically generated **Art. 117 protocol** (self-invoice/reverse charge mechanism).

## ✅ Before you start
- The vendor must have a correct **EU country** and a valid **VAT number**, verified via VIES.
- Check that your own company has valid VAT registration for intra-community transactions (usually the default for VAT-registered entities).

## 🧾 Step by step
1. Create the purchase order normally — pick the vendor, add products/services and quantities.
2. At the order level there is **no** specific "EU purchase" field — this is normal, expected behavior.
3. Confirm the order and receive the goods, if it's a physical delivery (`stock.picking`).
4. Create the vendor bill — here the **EU B2B** fiscal position should load automatically based on the vendor's country/VAT number.
5. Check on the bill that an Art. 117 protocol is generated — see the full scenario in the VAT administration manual.

## 📂 What gets generated
- At the order level — nothing Bulgaria-specific.
- At the bill level — an `account.move.bg.protocol` for self-charging the due and deductible VAT.

## ⚠️ Common mistakes
- Expecting the order to show "EU supply" — that information only appears on the bill.
- A vendor with an invalid/unverified VAT number → the bill may get the wrong fiscal position (e.g. Domestic instead of EU B2B).
- Mixing up goods (Art. 84) with services (Art. 82(2)) — the two cases lead to different protocols; check the nature of the purchase.

## 🔗 Related
The full step-by-step scenario on the bill — *EU B2B — Purchase (ICA)* in the VAT administration manual (`l10n_bg_tax_admin_manual`).
