The **l10n_bg_stock_account** module enables automatic stock accounting journal entries
at picking validation for **manual/periodic costing** products in Bulgarian companies.

**Problem Solved**

Standard Odoo 19 only creates accounting entries at picking time for products using
real-time (perpetual) costing. Bulgarian companies using manual/periodic costing do not
get a journal entry when goods are received — accounting is deferred to a periodic closing.

This module bridges the gap: it allows individual product categories to opt in to
**automatic journal entry generation at picking validation**, without changing the
product's cost method or valuation setting.

**New Flag: "Auto-post stock accounting on validate"**

A new Boolean field ``l10n_bg_stock_auto_post`` (company-dependent) is added to
``product.category``. When enabled for a category:

- **At picking validation** — a journal entry is created immediately, valued at the
  PO (purchase order) unit price × received quantity:

  - Dr. Stock Valuation Account (302 / 303 / 304 — from category)
  - Cr. Stock Variation Account (GRNI / clearing — linked to valuation account)

- **At vendor bill posting** — the invoice line account is automatically set to the
  **Stock Variation Account** (instead of the default expense account):

  - Dr. Stock Variation Account (GRNI / clearing)
  - Cr. Accounts Payable (401)

If invoice price equals PO price, the GRNI account nets to zero. If there is a price
difference, the residual is cleared by the companion module ``l10n_bg_stock_price_diff``.

**Price Difference Accounts**

Two optional accounts on the product category (used by ``l10n_bg_stock_price_diff``):

- **Price Difference Account (+)** — clearing when invoice > PO
- **Price Difference Income (−)** — direct income when invoice < PO

**Technical Implementation**

Three surgical overrides — no changes to ``product.valuation``, no Anglo-Saxon engine:

- ``stock.move._should_create_account_move()`` — allows entry creation for incoming
  moves of auto_post categories (bypasses the ``real_time`` requirement)
- ``stock.move._get_account_move_line_vals()`` — returns Dr. valuation / Cr. variation
  instead of location-based accounts
- ``account.move.line._compute_account_id()`` — on vendor bills, sets the line account
  to stock_variation (GRNI) for auto_post manual_periodic products

For Bulgarian companies (``anglo_saxon_accounting = False``), the Odoo v19 Anglo-Saxon
price difference engine is entirely skipped — no blocking needed.
