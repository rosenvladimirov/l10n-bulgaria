# Changelog

All notable changes to `l10n_bg_tax_admin` are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [16.0.3.1.0] - 2026-07-25

Backport of isolated O19 fixes (wave 1). Feasibility analysis verified against
the O19 source; P6 (import VAT base) and the full MRN subsystem are intentionally
left for the O19 migration.

### Added
- **VAT protocol narration from product lines** (backport of O19): an invoice's
  VAT-ledger narration is now assembled from its product line names (joined with
  `", "`) when the result is ≤ 50 characters; otherwise the fiscal mapper's
  default narration is kept. Applied to the main invoice only.
- **MRN field on customs declarations** (`account.move.bg.customs.mrn`): manual
  20-character Movement Reference Number with a uniqueness constraint and an
  upper-case/strip onchange (empty result → NULL to avoid unique collisions).
  Entered manually from the real customs document. No auto-assembly / check-digit.

### Fixed
- **Art. 117 protocol numbering gap/duplicate on reset-to-draft**: resetting a
  posted protocol to draft no longer unlinks its wrapper, so re-posting keeps the
  original protocol number instead of consuming a new sequence number. When a
  repost changes the fiscal position so the document is no longer a protocol, the
  now-orphaned wrapper is cleaned up in `_post` (avoids a stale wrapper writing a
  protocol number onto a non-protocol invoice). `l10n_bg_protocol_invoice_id` is
  `copy=False` so duplicating a posted protocol invoice does not share its wrapper.
- **Protocol numbers are always 10 digits.** `_get_starting_sequence` starts an
  empty sequence at `"0000000001"`; `_get_last_sequence` left-pads the last value
  to 10 digits **only for a purely numeric result** (so an 8-digit history like
  `00000115` continues as `0000000116`, `0000000117`, … — continuous, no restart).
  Slice (not replace-all) preserves internal zeros; non-numeric results are left
  untouched. Existing posted protocol numbers are **not** migrated — only new
  numbers are emitted 10-digit.

### Safeguards
- Customs `mrn` is normalized (upper-case, spaces stripped, empty → NULL) on all
  write paths (`create`/`write`, not only the UI onchange) so RPC/import cannot
  bypass the uniqueness guarantee or defeat de-duplication via case variants.

*Assisted by Claude Code*
