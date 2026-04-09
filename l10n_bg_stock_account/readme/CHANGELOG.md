# Changelog

## 19.0.1.0.0

- Initial release
- New field `l10n_bg_stock_auto_post` (Boolean, company-dependent) on `product.category`
- New fields `l10n_bg_price_diff_account_id` and `l10n_bg_price_diff_income_account_id`
  on `product.category` (used by companion module `l10n_bg_stock_price_diff`)
- Override `stock.move._should_create_account_move()`: allows journal entry creation
  at picking validation for incoming moves of auto_post categories (bypasses
  the `real_time` requirement for manual/periodic products)
- Override `stock.move._get_account_move_line_vals()`: BG standard entry
  Dr. stock_valuation_account / Cr. account_stock_variation (GRNI clearing)
- Override `account.move.line._compute_account_id()`: on vendor bills, sets
  invoice line account to stock_variation (GRNI) for auto_post manual_periodic products
- View: inherit `stock_account.view_category_property_form` — adds auto_post flag
  and "BG Auto-post Accounts" group (visible when flag is enabled)
