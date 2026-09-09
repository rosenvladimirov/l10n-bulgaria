# Changelog — l10n_bg_hr

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [19.0.2.9.2] - 2026-09-09

### Changed
- TELK decisions are now ordered by **issue date** (`date_decision`), not by
  the start of their validity period. The two diverge: a re-assessment issued
  in December may only take effect in January, so ordering by `date_from` put
  the older decision on top while the newer one "waited" — and the payroll
  officer reads the list as a history of what was issued.
  `latest_for()` follows the same order, so the decision shown on the employee
  is the newest one issued.

## [19.0.2.9.1] - 2026-09-08

### Fixed
- Opening a TELK decision form raised
  `AttributeError: 'l10n_bg.telk.decision' object has no attribute
  '_get_thread_with_access'` (reported on poligroup-v19).
  🚨 The view has carried `<chatter/>` since the model was ported from the
  `-v20` tree in `cd65304` — the same commit — but the model itself came over
  without `mail.thread`, so the web client asked for mail data the record
  could not answer. The fix is on the model, not the view: the precedent in
  this very module is `hr.version.amendment`, which is also a document
  carrying rights and is also tracked.
- `l10n_bg.telk.decision` now inherits `mail.thread` and
  `mail.activity.mixin`. `number`, `percent`, `date_from` and `date_to` are
  tracked — those four are exactly the fields whose change moves the rights
  hanging on the decision (Art. 18(2) PITA relief, the 26-day leave under
  Art. 319 LC). The activity mixin also gives the expiry a place to be
  reminded from, which is the whole point of the register.

### Note
🔄 The model lives in two trees with independent histories (here and
`l10n_bg_version` in `-v20`). This change adds fields to the model, so it has
to be carried over by hand, or one `_name` ends up with two incompatible
shapes — exactly what the model's own docstring warns about.

*Assisted by Claude Code*
