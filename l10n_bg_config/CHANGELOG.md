# Changelog

All notable changes to the l10n_bg_config module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
