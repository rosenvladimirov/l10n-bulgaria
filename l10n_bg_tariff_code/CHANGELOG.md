# Changelog

All notable changes to the l10n_bg_tariff_code module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.3.0.11] - 2026-04-07

### Changed
- Renamed view group names to include `l10n_bg` prefix (`l10n_bg_tariff_rate`, `l10n_bg_taric_rates`, `l10n_bg_taric_integration_container`) for compatibility with `l10n.bg.config.mixin` visibility engine
- Removed mixin inheritance from models — centralized in `l10n_bg_config`
- Removed `l10n_bg_config` from depends (mixin is inherited upstream)

## [18.0.3.0.10] - 2026-03-01

### Added
- Initial changelog entry
