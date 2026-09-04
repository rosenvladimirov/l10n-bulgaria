# Changelog

All notable changes to the l10n_bg_config module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.8.6.14] - 2026-09-04

Lockstep port of l10n_bg_config 19.0.8.6.5 → 19.0.8.6.14 (registration
hardening + small fixes). The insignificant-value threshold (19.0 8.7.x) and
the DEF-154 work-calendar mixin (19.0 8.8.0) are deliberately NOT ported yet:
their consumers (l10n_bg_tax_admin stock_picking, payroll-ee) are not on 18.0.

### Added
- `data/l10n_bg_registration_data.xml` (noupdate): seeds
  `l10n_bg.register_server_url` = https://www.odoo-shell.dev and
  `l10n_bg.register_enabled` = 1. Without it `server_url` was empty on every
  18.0 install, so the registration push never left the instance (bus +
  local record only). The per-client token is NOT in data (public repo); it
  is provisioned by the server on the first push (see Fixed).
- Migrations `18.0.8.6.5` / `18.0.8.6.6` / `18.0.8.6.7` (post-migrate):
  registration ping on upgrade (`post_init_hook` runs only on a fresh
  install), force-set server URL + enabled on already-installed databases,
  re-ping with the corrected EE detection. Verbose logging.
- Migration `18.0.8.6.14`: account 491 „Доверители" → `reconcile = True` on
  existing databases (matching template row added for new installs).
- `_rec_names_search` on `l10n.bg.kid` (`code`, `name`) and
  `l10n.bg.account.kid.rule` (`account_code`, `note`): `_rec_name` is a
  computed non-stored `display_name`, so the stock `name_search` could not
  find records by code.

### Fixed
- Registration: bootstrap token provisioning. The first push goes without a
  token; the server answers with a per-client token which is stored in
  `l10n_bg.register_token` for subsequent pushes (19.0 b10a1f4).
- Registration: EE-module detection counts `state IN ('installed',
  'to upgrade')`, so the ping issued from post-migrate during a combined `-u`
  still sees the sibling EE modules (19.0 78101cd).
- Duplicate visible document-number field on the move form: `l10n_bg_name`
  (related alias of `l10n_bg_document_number`) is now invisible; the visible
  field stays `l10n_bg_document_number` from `l10n_bg_reports_config`.
- Alt+Shift+K API-key generation on the partner form: view
  `view_res_partner_form_api_key` (`js_class=api_key_res_partner_form`) had
  been `active=False` since 2026-03-25 (slipped in with an unrelated
  l10n_bg_api_nra commit); back to `active=True`. `form_view.js`: `_t` with a
  template literal replaced by `_t("… %s", result)`.
- Chart template: account 491 „Доверители" (`l10n_bg_491`) defined as
  reconcilable. It holds money kept by third parties on our behalf (COD
  couriers, fulfillment partners, intermediaries) and must be matched against
  their settlements.

### Changed
- Explicit `web` dependency (backend assets live in `web.assets_backend`).

## [18.0.8.3.1] - 2026-05-16

### Fixed
- Upgrade-time initialization now actually runs. The manifest previously
  declared a `post_migrate_hook` key, which **stock Odoo does not honor**
  (only OpenUpgrade does), so on every database upgraded past 18.0.8.2.0
  the `l10n_bg.blacklist_key` parameter and the
  `res_company.is_l10n_bg_multilanguage` JSON were never populated
  (Settings → Bulgaria showed "No data", `/l10n_bg/blacklist/check`
  would fail).

### Changed
- Removed the dead `post_migrate_hook` manifest key and function, and
  the now-stale `post_migrate_hook` re-export in `__init__.py` (its
  presence raised `ImportError` on module load once the function was
  gone).
- Added `migrations/18.0.8.3.1/post-migrate.py` performing the same
  idempotent backfill (`_init_blacklist_key` + multilanguage inverse)
  on `-u`, for all companies.

## [18.0.8.2.1] - 2026-04-16

### Changed
- Blacklist JS service (`l10n_bg_blacklist`) temporarily disabled via early return
  in `start()` — blocking overlay and sticky warning notifications are no longer
  shown. Controller, encrypted file and bus channel remain in place; to re-enable
  remove the early return in `static/src/services/blacklist_service.js`.

## [18.0.8.2.0] - 2026-04-09

### Added
- Blacklist mechanism: encrypted `data/blacklist.enc` (Fernet) with VAT-based lookup
- Controller `/l10n_bg/blacklist/check` — decrypts file using key from `ir.config_parameter`
- OWL service `l10n_bg_blacklist`: sticky warning notification for blacklisted companies,
  non-dismissable overlay when security file is missing or corrupted
- `post_migrate_hook` for upgrade compatibility from older versions
- CLI tool `tools/update_blacklist.py` for managing the encrypted blacklist file
- External dependency: `cryptography` (Fernet encryption)

## [18.0.8.0.5] - 2026-04-07

### Added
- `account.move.line` now inherits `l10n.bg.config.mixin` — enables automatic hiding of `l10n_bg_*` fields and groups in move line views for non-BG companies

## [18.0.8.0.4] - 2026-03-01

### Added
- Initial changelog entry
