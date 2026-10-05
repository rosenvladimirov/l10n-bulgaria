# Changelog

## [18.0.1.0.0] - 2026-10-05

### Added — Labour Code layer extracted from `l10n_bg_hr_payroll`

- Moved from `l10n_bg_hr_payroll` 18.0.18.11.0 with unchanged names and definitions: the Art. 66 LC contract fields, the related employee fields, `hr.contract.type` duration, the 21 contract types, the contract number sequence, and the contract amendment model `l10n_bg.hr.contract.amendment` with its views, access rights and rule. `pre_init_hook` transfers the ownership of the existing xmlids (explicit list, checked by `tools/check_xmlid_transfer.py`).
- Amendment behaviour from 19.0 adapted to `hr.contract`: own legal basis and signatures (no `_inherits` of the contract), snapshot of the previous terms at creation, activation on the contract on the effective date (cron), early activation, reset to draft, temporary assignment under Art. 120 LC (45 calendar days per year) and return on expiry from the snapshot, lock after activation, signing after the effective date is a warning.
- New from 19.0: TELK/NELK decision register; employee ID card, protection status, personal doctor, disability decision expiry, foreign tax number, KID code and workplace code; expiring documents cron; fixed-term end, expected contract type after the term and the two fixed-term crons (in 18.0 the overdue one only flags the contract); total leave days; KID on the job position and the company.
