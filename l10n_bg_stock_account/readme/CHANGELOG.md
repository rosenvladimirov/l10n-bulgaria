# Changelog

## 19.0.1.7.0

- Сметките за брак/липси (`l10n_bg_stock_loss_account_id`) и за излишъци
  (`l10n_bg_stock_gain_account_id`) на `product.category` вече се виждат и
  редактират във формата — в групата „BG Auto-post Accounts“, под Stock Output.
  Досега полетата ги имаше в модела, но не и в изгледа: сметката, която решава
  как се осчетоводява бракът, не можеше да се провери от екрана, а нова
  категория оставаше без нея и бракът тихо падаше на Stock Output.
- Бутон „Journal Entries“ на документа за брак (`stock.scrap`) — същият като на
  пикинга: брой статии през `move_ids.account_move_id`, отваря статията
  директно при една. Нов файл `models/stock_scrap.py`, изглед
  `views/stock_scrap_views.xml`.
- Права: бутонът „Journal Entries“ на пикинга и на брака е с
  `groups="account.group_account_readonly"`. Без това складов потребител без
  счетоводни права виждаше бутона.

## 19.0.1.6.3

- Сметката на виртуалната локация в BG auto-post: обикновено движение към/от
  локация тип `inventory` с попълнен `valuation_account_id` (Loss Account) се
  осчетоводява по сметката на локацията вместо по Stock Output / Stock Input на
  категорията. Пример: „Мостри за клиенти“ с 615 → Дт 615 / Кт 303 вместо
  Дт 701.100 / Кт 303; връщането — Дт 303 / Кт 615.
- Брак и инвентаризация остават на loss/gain сметките на категорията; без сметка
  на локацията поведението е както досега. Нов helper
  `_l10n_bg_counterpart_location_account()`.

## 19.0.1.5.0

- Права фикс: полето „BG Auto-post Accounting" и групата „BG Auto-post Accounts"
  на product.category вече са с `groups="account.group_account_readonly"` —
  идентично с ограничението на стандартните „Account Properties". Преди се
  виждаха на всеки (вкл. складови потребители без счетоводни права).
  (Пренесено от feat/erpnet-split d65c632 при финализиране на split-а.)

## 19.0.1.4.0

- Landed Costs for BG auto-post products (GAP 1 fix): core `stock_landed_costs`
  skips journal entries for products with `valuation != 'real_time'` while still
  updating the move value — for auto_post (periodic) categories this left the GL
  stock valuation account short by the landed cost amount and double-counted the
  expense (once via the service vendor bill, once inside the higher issue value).
- New override `stock.landed.cost.button_validate()`: after the core entry, posts
  a separate BG journal entry for auto_post periodic products using the core
  `_create_accounting_entries()` logic — Dr. stock valuation (302/303) /
  Cr. cost line account (e.g. 301 GRNI), prorated by remaining quantity.
  Plain periodic products (without the BG flag) keep standard behaviour.
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
