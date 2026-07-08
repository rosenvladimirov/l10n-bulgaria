# Changelog

All notable changes to the l10n_bg_hr_holidays module will be documented in this file.

## [19.4.2.1.8] - 2026-07-08

### Fixed — Leave Types list EvalError (Пламена 156424)

- Consolidated the duplicate `l10n_bg_allow_paid_days` list field into a single `optional="hide"` column, dropping the self-referential `column_invisible` that threw `EvalError`. Lockstep of 19.0.1.10.10.

*Assisted by Claude Code*
