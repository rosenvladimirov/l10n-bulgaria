# 📦 Guide — Stock Auto Accounting (Bulgaria)

Module **l10n_bg_stock_account** — automatic journal entries on stock picking validation for products using **manual/periodic** costing.

## 📘 What the module does
Standard Odoo 19 posts accounting entries on stock moves **only** for `real_time` (perpetual) costing products. Bulgarian companies running **periodic** inventory get no entry when goods are received.

This module bridges the gap: it lets **selected product categories** generate a journal entry at picking validation, following the Bulgarian standard:

```
Dr. Stock valuation account (302/303/304)
    Cr. Stock variation / transit account (301 / GRNI)
```

…without switching the category's `property_valuation` to `real_time`.

## ⚙️ Configuration (per product category)
**Inventory → Configuration → Product Categories → [category]**, the stock accounts section:

| Field | Role | Example |
|---|---|---|
| **Auto-post stock accounting on validate** | Enables auto-posting when a receipt is validated | ✔ |
| **Stock Input Account** | Transit account credited on receipt (debited by the vendor bill) | 301 |
| **Stock Output Account** | COGS/expense account on outgoing moves | 702.100 |
| **Stock Loss Account (scrap/shortage)** | Debited on scrap or negative inventory adjustment | 669.200 |
| **Stock Gain Account (surplus)** | Credited on positive inventory adjustment | 709.000 |
| **Price Difference Account (+)** | Clearing when invoice > PO price (for `l10n_bg_stock_price_diff`) | clearing |
| **Price Difference Income (−)** | Income when invoice < PO price | 709 |

> Fields are **company-dependent** — set them per company. If an account is missing, the system falls back: Loss → Output, Gain → Input, Input → stock variation.

## 🧾 Workflow

### Receipt
1. The product's category has **Auto-post** enabled.
2. **Validate** the receipt.
3. An entry is created automatically: **Dr. Stock valuation (302) / Cr. Stock Input (301)**.
4. Later, when the vendor bill is posted, 301 is debited against the supplier.

### Delivery / consumption
1. Outgoing move of a product in an Auto-post category.
2. Entry: **Dr. Stock Output / COGS (702.100) / Cr. Stock valuation (302)**.

### Scrap / Inventory adjustment
- Scrap or a **negative** adjustment → **Dr. Stock Loss (669.200) / Cr. Stock valuation**.
- A **positive** adjustment (surplus) → **Dr. Stock valuation / Cr. Stock Gain (709.000)**.

> ⚠️ Without a dedicated Loss account, scrap is booked to Output (COGS) — accounting-wise inaccurate (scrap ≠ a realized sale). Set 669.200.

## 🔗 Viewing the generated entries
On the picking there is an **"Account Moves"** field/button (`l10n_bg_account_move_ids`) showing the related journal entries. With a single entry it opens it directly; with several, a list.

## 🤝 Interaction with price differences
Together with **l10n_bg_stock_price_diff**: when the invoice price differs from the PO price, the difference goes through the **Price Difference Account (+)** (clearing, distributed along the production chain) or directly to **Price Difference Income (−)** when the invoice is lower.

## ❓ Common mistakes
- **No entry appears** → check that the category has **Auto-post** enabled and a stock account set for the current company.
- **Scrap booked to COGS** → set a **Stock Loss Account** (otherwise it falls back to Output).
- **Duplicate entries** → do not combine Auto-post with `real_time` valuation on the same category; Auto-post is for manual/periodic.
- **Wrong company** → accounts are company-dependent; verify they are set for the right company.

## 🔗 Related
`l10n_bg_stock_price_diff` (price differences), `stock_account` (base). For VAT/invoicing see the *VAT Administration* guide.
