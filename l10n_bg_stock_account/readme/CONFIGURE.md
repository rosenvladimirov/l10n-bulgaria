Before enabling auto-post on a category, ensure:

1. The **Stock Valuation Account** (``property_stock_valuation_account_id``) is set on the
   category (e.g. account 302, 303, or 304).
2. The **Stock Variation Account** (``account_stock_variation_id``) is set on the valuation
   account — this is the GRNI / clearing account (Accounting → Chart of Accounts → open
   the valuation account → field "Stock Variation Account").
3. The **Stock Journal** is configured at company level (Accounting → Configuration →
   Settings).

**Enabling Auto-post on a Product Category**

1. Go to **Inventory → Configuration → Product Categories**.
2. Open the category (e.g. "Raw Materials").
3. In the **Accounting Properties** section, check **"Auto-post stock accounting on validate"**.
4. The **BG Auto-post Accounts** group appears — fill in **Stock Journal** (required).
   Optionally set **Price Difference Account (+)** and **Price Difference Income (−)**
   (only needed when ``l10n_bg_stock_price_diff`` is installed).
5. Save the category.

**Verifying the Setup**

After configuration, validate a receipt for a product in the configured category.
Check the picking's **Valuation** smart button — you should see::

    Dr.  302 / 303 / 304   [PO price × qty]
    Cr.  GRNI (clearing)   [PO price × qty]

Post the matching vendor bill — the invoice line account should be set to GRNI
(Stock Variation), and the GRNI account should net to zero when PO = Invoice price.

**Notes**

- The flag is **company-dependent** — can be enabled per company independently.
- Works alongside products with real-time costing — no conflicts.
- Non-storable products (consumables, services) are unaffected.
