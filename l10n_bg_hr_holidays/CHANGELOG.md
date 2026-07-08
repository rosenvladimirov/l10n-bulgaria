# Changelog

All notable changes to the l10n_bg_hr_holidays module will be documented in this file.

## [19.0.1.10.10] - 2026-07-08

### Fixed — Leave Types list crashed with EvalError (Пламена 156424)

- The `hr.leave.type` list view had a duplicate `l10n_bg_allow_paid_days` field where the optional column carried `column_invisible="not l10n_bg_allow_paid_days"` — self-referential, so evaluating it in the optional-columns menu (where the field value is out of scope) threw `EvalError: Name 'l10n_bg_allow_paid_days' is not defined`. Consolidated to a single `optional="hide"` column without the broken expression.

*Assisted by Claude Code*
