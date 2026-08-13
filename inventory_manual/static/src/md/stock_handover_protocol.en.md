# 🧾 Handover Protocol

> Module: **l10n_bg_report_stock** · Model: `stock.picking` · Report: **Handover protocol**

## 📌 When to use
When you need to document the physical handover of goods on delivery/receipt with both parties' signatures — common practice in Bulgarian logistics, separate from the invoice.

## ✅ Before you start
- The `l10n_bg_report_stock` module must be installed.
- The transfer (`stock.picking`) must exist; it doesn't need to be validated.

## 🧾 Step by step
1. Open the transfer (receipt, delivery, or internal transfer).
2. From the **Print** menu, select **Handover protocol**.
3. A QWeb PDF is generated, styled with the shared Bulgarian report theme, with signature fields for both the handing-over and receiving parties.
4. Print/sign the document physically at the time of handover.

## 📂 What gets generated
- A PDF document named **"Handover protocol - <partner> - <transfer number>"**.
- No accounting entry is created — a purely logistical/evidentiary document.

## ⚠️ Common mistakes
- Don't confuse it with the *Accepted-Delivery Slip* (Accepted delivery report) — the two are different reports with different purposes (the protocol is for physical handover, the slip is a representative document of the delivered goods).
- The positioning of text blocks (header/footer) on the report is managed by `l10n_bg_stock_picking_comment_template`, if installed — check there if formatting looks off.

## 🔗 Related
For the difference with the pro-forma document at the sale order level, see *Handover Protocol on the Sale Order* in the Sales manual.
