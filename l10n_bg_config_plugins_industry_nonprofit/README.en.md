# Bulgaria - Industry Pack: Non-profit (ЮЛНЦ) (КИД sector S)

LGPL-3 · part of `l10n-bulgaria` · depends on `l10n_bg_config`.

## Purpose

Configuration pack for КИД sector S — non-profit legal entities (regulated non-economic activity, membership fees, donations under СС 9).

This is one of the per-industry configuration plugins built on top of the
"one chart of accounts, many КИД" install filter in `l10n_bg_config`.
Installing it:

1. Adds КИД section **S** to every Bulgarian company's *Active КИД
   sectors* (`res.company.l10n_bg_kid_ids`).
2. Reloads the chart template (proven `post_init` reload pattern shared
   by all `l10n_bg_config_plugins_*` data plugins) so the filter lets
   sector S's sector-specific accounts through.

## Full pack — accounting content (PENDING)

The sector's own accounts / taxes / fiscal positions / analytic are
shipped via `data/template/*.csv` and merged automatically by the
`account.chart.template` plugin pipeline. These files are **empty by
design**: the content must come from sourced Bulgarian accounting
standards (НСС/ЗСч), never improvised. Populate, then list the CSVs in
`__manifest__.py` `data`.

## Design decision — КИД account-code rules stay centralized

Decided 2026-05-18 (Rosen): the full set of `l10n.bg.account.kid.rule`
records is the *definition of the install filter* and stays in
`l10n_bg_config_plugins_industry_map` (a rule is unique by
`account_code`; cross-sector rules 303/305/456/457 span A/C/F/D/G/H and
must not be duplicated, and keeping them central preserves the lean base
chart). Per-industry plugins therefore decompose only **activation** (the
КИД sector preset done here) and **content** (the sector's own
accounts/taxes/fiscal positions via `data/template/*.csv`). This plugin
ships **no** rule records by design.
