# 🌉 From Purchase Order to Vendor Bill — Fiscal Bridge

> Models: `purchase.order` → `account.move` · Related module: `l10n_bg_tax_admin`

## 📌 When to use
When you want to understand **why** nothing on the purchase order looks "Bulgarian" and what exactly happens once you click **Create Bill**. This is the conceptual bridge between the standard Odoo purchasing flow and Bulgarian VAT logic.

## ✅ Before you start
- Understand that `purchase.order`/`purchase.order.line` **contain no** Bulgarian localization fields — verified, there are none.
- The `l10n_bg_tax_admin` module (if installed) adds its logic exclusively at the `account.move` / `account.move.line` level — the vendor bill.

## 🧾 Step by step
1. Confirm and receive the purchase order normally — no Bulgaria-specific steps at this stage.
2. Click **Create Bill** — a draft vendor bill (`account.move`, `in_invoice`) is generated, pre-filled with the order's lines.
3. On the bill, the **fiscal position** is determined from the vendor's data (country, VAT number) — this is exactly where the logic for the following kicks in:
   - **Domestic** — local purchase, standard tax credit;
   - **EU B2B** — intra-community acquisition (Art. 84) → an **Art. 117 protocol** is auto-generated;
   - **0% Art. 82(2)** — service received under reverse charge → an Art. 117 protocol;
   - **Outside EU** — import (Art. 16) → a customs declaration and VAT on the customs value.
4. Check/adjust the tax on each bill line for the specific case.
5. Confirm the bill — the system generates the relevant protocol/declaration automatically where applicable.

## 📂 What gets generated
- Everything related to VAT treatment is generated at the bill level: `account.move.bg.protocol`, `account.move.bg.private`, `account.move.bg.customs` (depending on the scenario) — **never** at the order level.

## ⚠️ Common mistakes
- Trying to set a "fiscal position" on the purchase order — that field lives on the partner/bill, it carries no Bulgaria-specific logic on the order itself.
- Assuming the order "guarantees" correct VAT treatment — always check the bill before confirming, especially for EU/non-EU vendors.

## 🔗 Related
For the full fiscal-position scenarios (step by step on the bill) — see the *Guide to VAT Administration (Bulgaria)* manual (`l10n_bg_tax_admin_manual`): *EU B2B — Purchase*, *0% Art. 82(2) — Purchase*, *Outside EU — Purchase (Import)*.
