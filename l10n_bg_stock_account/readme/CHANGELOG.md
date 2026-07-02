# Changelog

## 19.4.1.3.0

- Production-move guard in `stock.move._get_account_move_line_vals()` (lockstep
  from 19.0.1.3.0): production consumption/output delegates to the standard
  location-based mechanism (Cost of Production account), so finished goods
  receipt posts Dr. 303 / Cr. 611 instead of Cr. 301 (GRNI), enabling
  `l10n_bg_mrp_account` (601 transit → 611) on top.
- Landed Costs for BG auto-post products (lockstep from 19.0.1.4.0): core
  `stock_landed_costs` skips journal entries for `valuation != 'real_time'`
  while still updating the move value. New `stock.landed.cost.button_validate()`
  override posts a separate BG entry for auto_post periodic products via the
  core `_create_accounting_entries()` — Dr. stock valuation (302/303) /
  Cr. cost line account (e.g. 301 GRNI), prorated by remaining quantity.
- New field `l10n_bg_account_move_id` on `stock.landed.cost` (idempotency +
  traceability), shown on the form next to the standard Journal Entry.
- New dependency: `stock_landed_costs`.

## 19.0.1.1.0

- Added `l10n_bg_stock_input_account_id` (Stock Input Account) on `product.category`:
  transit account credited at goods receipt (e.g. 301), debited when vendor bill is posted.
  Falls back to `account_stock_variation_id` if not configured.
- Added `l10n_bg_stock_output_account_id` (Stock Output Account) on `product.category`:
  COGS/expense account debited when goods are issued (e.g. 702.100).
- Updated `stock.move._get_account_move_line_vals()`:
  - Incoming: Dr. stock_valuation (302) / Cr. input_account (301) — replaces old 409 clearing
  - Outgoing: Dr. output_account (702.100) / Cr. stock_valuation (302) — new outgoing JE
- Updated `stock.move._should_create_account_move()`: extended to allow JE creation for
  outgoing moves (`is_out`) in addition to incoming moves
- Updated `account.move.line._compute_account_id()`: vendor bill lines now use
  `l10n_bg_stock_input_account_id` (301) with fallback to stock_variation (409)
- Added smart button on `stock.picking` form showing linked journal entries count;
  opens form view directly when only one entry exists
- View: new `stock_picking_views.xml` — smart button in button_box
- View: `product_category_views.xml` updated — new accounts visible in "BG Auto-post Accounts" group

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
