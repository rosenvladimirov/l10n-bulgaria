# Changelog

All notable changes to the l10n_bg_hr_holidays module will be documented in this file.

## [18.0.1.10.7] - 2026-07-08

### Fixed — Leave Types list EvalError (Пламена 156424)

- Consolidated the duplicate `l10n_bg_allow_paid_days` list field into a single `optional="hide"` column, dropping the self-referential `column_invisible` that threw `EvalError`. Lockstep of 19.0.1.10.10.

*Assisted by Claude Code*

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.1.0.4] - 2026-03-01

### Added
- Initial changelog entry
