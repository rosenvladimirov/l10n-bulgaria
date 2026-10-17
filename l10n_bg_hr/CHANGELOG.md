# Changelog — l10n_bg_hr

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [19.0.2.9.18] - 2026-10-17

### Fixed
- The amendment migration (moved from 19.0.2.9.17 to 19.0.2.9.18) set the
  Art. 121a ground only where the column was NULL — but the column is born
  filled with the default `art119`, so postings kept Art. 119. It now matches
  by type. Re-runnable; on the pilot database (copy-clean-2909) 2.9.17 found
  nothing either way (225 imported "Other" agreements, no postings).

*Assisted-by: Anthropic/Claude-Opus-5-5-1m*

## [19.0.2.9.17] - 2026-10-17

### Changed — DEF-210 items 1–3 and 7: what an amendment changes (Пламена, ТГ 172092)
- **Checkboxes instead of one type**: wage, position, working time, paid leave,
  workplace, term. The form and the wizard show the pages of every ticked
  change, so one agreement can change wage and position together (the
  application already took all filled changes). `amendment_type` stays as a
  technical field computed from the boxes (one box → its type, several →
  "Other"); it is chosen by hand only without boxes — posting, additional
  duties, a textual agreement. An agreement with boxes is never textual.
- **Legal ground from a menu** (`l10n_bg_legal_basis`): Art. 119(1), order
  under Art. 118(3) (wage increase only), order under Art. 138a (working time
  only), Art. 121a(1)(1). The two orders are checked. The free text stays as
  notes.
- **ETZ ground of the amendment** (`l10n_bg_etz_change_code`, item 12 of
  Annex 1): wage 019, working time 020, term/position/leave/workplace 021 (also
  together with wage or working time), posting 018; empty = nothing to register
  (`l10n_bg_etz_registrable`). Open: wage + working time only — 019 is proposed.
- Migration (19.0.2.9.18): existing agreements get their box from the type;
  "Other" gets boxes from the filled new values. Imported agreements without
  any value (225 in training / Payroll-January) stay without boxes and are not
  offered an ETZ.

*Assisted-by: Anthropic/Claude-Opus-5-5-1m*

## [19.0.2.9.16] - 2026-10-17

### Fixed
- 172197 item 4 (Пламена): contract type **005** (Art. 68(1)(4) LC — until the
  position is filled by competition) gets the new duration type `competition`.
  It has no calendar term, so the fixed-term check no longer demands one and
  the contract can be saved; the fixed-term crons skip it (they need a term).

*Assisted-by: Anthropic/Claude-Opus-5-5-1m*

## [19.0.2.9.15] - 2026-10-17

### Fixed
- DEF-209 item 2 (Пламена, ТГ 172091): the contract type of an employment
  offers only the grounds of item 12 of Annex 1 to НВРЗ. New flag
  `hr.contract.type.l10n_bg_hiring_allowed`; it is off for **007** (a probation
  period is a clause under Art. 70 LC, not a ground) and **018–021** (grounds
  for an amendment). Both `contract_type_id` and the contract after the term
  filter on it. The types stay in the data for existing versions.

*Assisted-by: Anthropic/Claude-Opus-5-5-1m*

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
