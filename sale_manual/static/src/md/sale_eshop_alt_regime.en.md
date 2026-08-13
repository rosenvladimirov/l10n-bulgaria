# 🛒 Online Store — NRA Alternative Regime

> Module: **l10n_bg_eshop_alt** (l10n-bulgaria-ee) · Data source: `sale.order` (confirmed orders) + the linked invoice

## 📌 When to use
Only for online stores operating under the **alternative reporting regime** of Ordinance N-18 — i.e. **without a fiscal device and without SUPTO software**. If the business uses a fiscal printer (`l10n_bg_erp_net_fp`) or a SUPTO solution, this regime does not apply.

## ✅ Before you start
- The `l10n_bg_eshop_alt` module must be installed (requires the Enterprise repo `l10n-bulgaria-ee` and `l10n_bg_api_nra`).
- All online orders for the reporting month must be **confirmed** (`sale.order`, state `sale`) with an invoice generated.
- Online store data configured: domain name, e-shop type.

## 🧾 Step by step
1. Confirm orders from the online store normally throughout the month — the **Sales** app requires nothing special from the salesperson.
2. At the end of the reporting period, open the NRA declaration menu and start the **Generate E-Shop Audit…** wizard.
3. Pick **year** and **month** — the wizard automatically collects all `sale.order` records confirmed in the period, together with the numbers/dates of the linked invoices.
4. The system generates an audit XML file per the official XSD schema (`dec_audit.xsd`, Windows-1251 encoding), including orders, line items, and refunds (full/partial cancellations).
5. Download and submit the XML file to the NRA.

## 📂 What gets generated
- `nra.declaration.eshop.order(.line)` and `.refund` records — a snapshot of the month's online orders for audit.
- A final XML file, validated against the NRA's official XSD schema.

## ⚠️ Common mistakes
- Unconfirmed orders (left as draft/quotation) are not included in the audit — check the status before generating.
- Refunds/cancellations made outside the standard credit-note flow may not be picked up automatically.
- If the business actually uses SUPTO or a fiscal printer — this regime/declaration **does not apply**, don't submit it unnecessarily.

## 🔗 Related
For the general sales process, see *Sales Process Overview*.
