# 🧾 Handover Protocol on the Sale Order

> Module: **l10n_bg_sale_order_delivery_note** · Model: `sale.order` · Report: **Accepted delivery report**

## 📌 When to use
Bulgarian commercial practice often requires a handover / pro-forma document issued at the **sale order** level — before or instead of the warehouse (stock-side) protocol. Use it when the customer expects a document acknowledging the goods at/before delivery, separate from the invoice.

## ✅ Before you start
- The `l10n_bg_sale_order_delivery_note` module must be installed.
- The **Pro-forma Invoices** setting (`sale.group_proforma_sales`) must be enabled for the user — the report is only available to that access group.
- The sale order must exist (it doesn't need to be confirmed) with lines filled in.

## 🧾 Step by step
1. Open the sale order.
2. From the **Print** menu, select **Accepted delivery report**.
3. The report is generated as a QWeb PDF, styled with the shared Bulgarian report theme (`l10n_bg_report_theme`) — with logo, company details, and a signature field.
4. Print/send the document together with, or before, the delivery.

## 📂 What gets generated
- A PDF document named **"Accepted delivery report - <order number>"**.
- No accounting entry is created — this is a purely representative (pro-forma) document, it does not replace the invoice.

## ⚠️ Common mistakes
- The option is missing from the Print menu → check that the current user is in the **Pro-forma Invoices** access group (Sales → Settings → Access Rights).
- Don't confuse this document with the warehouse handover protocol from `l10n_bg_report_stock` — that one is on the `stock.picking` level, not the order level. See the next section for the difference.

## 🔗 Related
The warehouse-side variant of the protocol (on the delivery/transfer level) — see *Handover Protocol* in the Inventory manual.
