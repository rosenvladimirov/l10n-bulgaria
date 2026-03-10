# Changelog

All notable changes to the l10n_bg_reports_audit module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.12.0.2] - 2026-03-10

### Fixed
- Fix tax tag leaking between moves in `_l10n_bg_apply_tax_tag()` - when processing lines from multiple moves in a batch, the tag from the first move with `l10n_bg_tax_tag_id` set was incorrectly applied to all subsequent moves' lines, causing wrong amounts to appear under declaration tags (e.g. tag 71)
- Remove unused `imd_tag_tax` LEFT JOIN from all SQL report views (`account_bg_vat_prepare_declar`, `account_bg_vat_sales_line`, `account_bg_vat_purchases_line`, `account_bg_vat_vies_line`) - the join was never referenced in SELECT/WHERE/GROUP BY and could cause row duplication inflating reported amounts

## [18.0.12.0.1] - 2026-03-01

### Added
- Initial changelog entry
