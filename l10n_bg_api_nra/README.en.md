# Bulgaria — NRA API Integration (core)

> The submission backbone for filing declarations to the Bulgarian
> National Revenue Agency (НАП) over its public API, with qualified
> electronic-signature (КЕП) signing in the browser.

**Module:** `l10n_bg_api_nra` | **Version:** 18.0.1.4.2 | **License:** LGPL-3 | **Category:** Accounting/Localizations | **Application:** Yes (standalone NRA app)

## Overview

`l10n_bg_api_nra` is the transport + signing core that every
declaration-specific module (D1, D6, VAT, VIES, ETZ, Naredba H-18
e-shop) builds on. It owns the HTTP client, the test/production
endpoint switch, the wallet-backed access-token sharing, and the
client-side КЕП signing dialog. Declaration content/format lives in
the sibling `l10n_bg_api_nra_*` and `l10n_bg_hr_payroll_nra_*`
modules; this module gets the signed payload to НАП and back.

It is registered as a **standalone Odoo application** (its own root
menu + NAP vector icon) rather than buried under Accounting.

## Architecture

### `nra.api.provider`

The raw HTTP client.

- `_get_base_url()` — reads `ir.config_parameter`
  `l10n_bg_api_nra.base_url` (falls back to the built-in NRA API base).
- `_get_submit_endpoint(company)` — resolves the full submit URL based
  on the company's **test vs production** mode, so the same code path
  exercises the НАП sandbox or live without edits.
- Endpoint path constants are appended to the resolved base.

### `nra.declaration` (abstract parent) + concrete declarations

| Model | Declaration |
|---|---|
| `nra.declaration` | shared state machine + submit/poll plumbing |
| `nra.declaration.d1` (+ `.d1.line`) | Декларация Образец 1 |
| `nra.declaration.d6` (+ `.d6.line`) | Декларация Образец 6 |
| `nra.declaration.vat` (+ `.vat.line`) | ДДС declaration |
| `nra.declaration.vies` | VIES declaration |
| `nra.declaration.h18_eshop` (+ `.h18.line`, `.h18.line.art`, `.h18.refund`) | Наредба Н-18 e-shop sales register (`action_collect_h18_orders`, `action_h18_generate_xml`) |

XSD schemas ship under `data/xsd/` and validate payloads before submission.

### Wallet-backed token sharing (`res.users`)

NRA access tokens are not stored per-user in clear text. The token
**owner** (`company.l10n_bg_nra_token_user_id`) holds the
`nra_access_token` key in their `l10n_bg_bank_wallet`. When another
user submits, the module copies the key from the owner's wallet into
the acting user's wallet (skipping if the user *is* the owner, and
purging stale keys first). This means a team can file declarations
without each member holding raw credentials.

### Client-side КЕП signing

`static/src/js/kep_signer.js` + `sign_submit_dialog.js` +
`sign_submit_widget.js` (+ QWeb `sign_submit_dialog.xml`) implement
the qualified-electronic-signature flow **in the browser** — the
private key never leaves the client. `controllers/main.py` handles the
sign/submit round-trip endpoints.

### Extended models

| Model | Addition |
|---|---|
| `res.company` | `l10n_bg_nra_token_user_id` (token owner) + test/prod mode |
| `res.users` | wallet token-copy logic on submit |
| `hr.employee` | `_l10n_bg_nra_declaration_lookups`, `action_view_l10n_bg_nra_declarations` |

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| (accounting/HR base) | `l10n_bg_config`, `l10n_bg_bank_wallet` |

`l10n_bg_bank_wallet` is mandatory — it is where the encrypted NRA
access token lives.

## Configuration

1. Install (registers the NRA application + icon).
2. Settings → set the company's test/production NRA mode and
   `l10n_bg_nra_token_user_id` (the credential owner).
3. The token owner authenticates once; their wallet stores the access
   token. Other users inherit it transparently on submit.
4. (Optional) override `l10n_bg_api_nra.base_url` in
   `ir.config_parameter` to point at a custom/sandbox gateway.

## Downstream consumers

`l10n_bg_api_nra_dec1`, `_dec6`, `_etz`, `_vat`, `_noi*`,
`l10n_bg_hr_payroll_nra_*`, `l10n_bg_account_nra_vat` — all delegate
transport + signing here.

## Known limitations

- Token sharing assumes one credential owner per company; multi-owner
  rotation is manual.
- КЕП signing requires the browser-side signing extension/driver on
  the client machine.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- NRA form formats: `claude.ai/memory/reference_nra_obr55_okd5_formats.md`
- Cross-repo map: `claude.ai/L10N_BG_ECOSYSTEM.md`

---

## Roadmap — Bulgarian NRA & NSSI declaration coverage

**Reference:** 30 official NRA XSD schemas (2025/2026 batch) cover
10 declaration topics. Tracking against this catalog gives a single
source of truth for what is implemented, what is partial, and what
remains.

### Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Production-ready: backend + XML build + XSD validation + UI |
| ⚠️ | Partial: XSD imported but XML build needs rewrite, or `declaration_type` extension still pending |
| ❌ | Not started: XSD available, no Odoo module |
| ⛔ | Out of scope: specialised domain, deliberately not implemented |

### Implementation matrix

| # | Topic | XSD file(s) | Module | Status |
|---|-------|-------------|--------|--------|
| 1 | **Declaration Form 1** (insured-person data, monthly) | CSV format (no XSD) | `l10n_bg_api_nra_dec1` + `l10n_bg_hr_payroll_nra_dec1` | ✅ |
| 2 | **Declaration Form 6** (aggregated monthly contributions) | No public XSD | `l10n_bg_api_nra_dec6` + `l10n_bg_hr_payroll_nra_noi` | ✅ |
| 3 | **ETZ Art.62 LC** (standard labour contract notice) | `etz_employ_restrict.xsd` | `l10n_bg_api_nra_etz` + `l10n_bg_hr_payroll_nra_etz` | ✅ |
| 4 | **ETZ Art.123 §5 LC** (employer succession) | `etz_123_employer.xsd` | XSD imported in `l10n_bg_api_nra_etz/data/`; `declaration_type='etz123'` **pending** | ⚠️ |
| 5 | **Statement Art.73 (1) ZDDFL** (non-labour income) | `SPR73_1.xsd` (root `<dec731>`) | `l10n_bg_api_nra_spr73` | ✅ |
| 6 | **Statement Art.73 (6) ZDDFL** (labour income, annual) | `dec73_6_publish.xsd` | `l10n_bg_api_nra_spr73` (XML build is reconstructed; **rewrite against XSD pending**) | ⚠️ |
| 7 | **VAT Declaration + journals** (monthly ZIP package) | No public XSD (CSV format) | `l10n_bg_api_nra_vat` + `l10n_bg_account_nra_vat` (per-file КЕП signing supported) | ✅ |
| 8 | **NSSI Appendix 9** (sick-leave certificate) | `Pril9.xsd` | `l10n_bg_api_nssi_pril9` | ✅ |
| 9 | **NSSI Appendix 10** (maternity, employer-issued) | `Pril10.xsd` | `l10n_bg_api_nssi_pril10` | ✅ |
| 10 | **NSSI Appendix 11** (maternity, self-employed) | `Pril11.xsd` | `l10n_bg_api_nssi_pril11` | ✅ |
| 11 | **DOPK Art.77 notification** (company closure/transformation) | No XSD (paper / PDF) | `l10n_bg_dopk_art77` (QWeb PDF wizard, model `ОКд-107`) | ✅ |
| 12 | **Intrastat** (EU goods/services) | No public XSD | `l10n_bg_intrastat` (XML generation, no XSD validation) | ⚠️ |
| 13 | **SAF-T** (Standard Audit File for Tax) | `BG_SAFT_Schema_V_1.0.2.xsd` (active from 01.01.2026), `V_1.0` (legacy) | — | ❌ |
| 14 | **Annual corporate tax (GDD Art.92 ZKPO)** | `dec92_2024_public.xsd` | — | ❌ |
| 15 | **High-fiscal-risk goods movements (SVFR)** | `decHfr_internal/import/export/thirdcountry_v5_restrict.xsd`, `API_decHfr_annul/confirm_v3_restrict.xsd` (6 schemas total) | — | ❌ |
| 16 | **E-commerce alternative reporting regime** (Ordinance N-18) | `dec_audit.xsd` | — | ❌ |
| 17 | **Fiscal-device monitoring (FDmon)** — 16 XSD schemas | `fbdata*.xsd`, `nra{common,req,res}.xsd`, `r{chng,dereg,reg}.xsd`, `req31/res31.xsd`, `xtask/ztask/xtiasutd/ztiasutd.xsd` | — | ⛔ specialised |
| 18 | **Postal-operator data (Art.25 ZNAP)** — 4 XSD schemas | `pos_25.xsd`, `pos_25_tpacc.xsd`, `trans_25.xsd`, `trans_25_tbpos.xsd` | — | ⛔ specialised |

### Execution plan

The plan is split into three phases: **finishing in-flight work**,
the **active development queue** (executed in strict order), and
**out of scope** specialised domains.

#### Phase A — Finishing in-flight work (immediate)

These items have backend models or imported XSDs already in place;
they are completed before any new module is started.

| # | Item | Module | Effort |
|---|------|--------|--------|
| A1 | **Statement Art.73 (6) XML rewrite** against `dec73_6_publish.xsd` — backend model exists but XML build is reconstructed from spec docs; align to official schema. | `l10n_bg_api_nra_spr73` (update) | 2–3 person-days |
| A2 | **ETZ Art.123 declaration type** — add `declaration_type='etz123'` selection on `nra.declaration` with the reduced 13-field schema. Pairs with DOPK Art.77 in succession workflows. XSD already imported. | `l10n_bg_api_nra_etz` (update) | 1–2 person-days |

#### Phase B — Active development queue (strict order)

Each module is started only after the previous one is production-ready.
SAF-T is deliberately scheduled last so it consolidates lessons from
earlier modules; its statutory effective date (01.01.2026) is tracked
separately as a hard deadline.

| # | Order | Item | Module | Effort | Notes |
|---|-------|------|--------|--------|-------|
| B1 | 1st | **E-commerce alternative regime** | `l10n_bg_eshop_alt` (new) | 2–3 person-days | Produces `dec_audit.xsd` for online stores not running СУПТО; smallest surface, ships first to validate the modular pattern for new declaration types. |
| B2 | 2nd | **Fiscal-device monitoring (FDmon)** | `l10n_bg_erp_net_fp_fdmon` (new) | 10–15 person-days | 16 XSD schemas covering NRA↔fiscal-device communication. A separate POS bridge (`l10n_bg_erp_net_fp_iot`) exists but speaks a different protocol stack. |
| B3 | 3rd | **Annual corporate tax declaration (Art.92 ZKPO)** | `l10n_bg_api_nra_dec92` (new) | 7–10 person-days | Every legal entity files by 30 June for the previous fiscal year. Source: GL + `l10n_bg_reports_audit`. |
| B4 | 4th | **SVFR — high-fiscal-risk goods movements** | `l10n_bg_svfr` (new) | 3–5 person-days | 6 XSD schemas + REST API for import / export / internal / third-country / annul / confirm flows. Required for wholesalers/transporters of fuel, textiles, mobile devices, etc. |
| B5 | 5th | **SAF-T (Standard Audit File for Tax)** | `l10n_bg_saf_t` (new) | 7–10 person-days | Monthly / annual / on-demand XML from `account.move.line` plus product/partner/tax metadata. Implemented last to consolidate the patterns developed in B1–B4. NRA Order З-ЦУ-30-1247/25.08.2025 effective from 01.01.2026 with graduated thresholds — track that deadline outside this queue. |

#### Phase C — Out of scope (do not implement unless explicitly required)

| Item | Reason |
|------|--------|
| **Postal-operator reporting (Art.25 ZNAP)** — 4 XSD schemas | Specialised domain (postal operators and money-transfer agents only); not part of the standard payroll / tax / audit workflow. 5–7 person-days if ever needed. |

### Verification workflow for new XSD imports

When integrating any future XSD:

1. Drop the file under `static/description/` (or `data/` for backwards
   compatibility) of the relevant declaration module.
2. Build a sample XML record set; validate with
   `xmllint --noout --schema /path/to/schema.xsd /tmp/sample.xml`.
3. If element names disagree with reconstructed naming, treat the
   XSD as authoritative — rewrite the `_build_*_xml()` method, do not
   override the schema.
4. Add a `_validate_*_xsd()` method that uses `lxml.etree.XMLSchema`
   so generation enforces the schema at runtime.
5. Re-test against the NRA client-side software (currently v17.03+
   for income statements; v20250603 for FDmon; etc.) before treating
   any module as production-ready.

### Source of truth

The 30-XSD catalog used for this gap analysis lives outside the
repository (private mirror, crawled from `nra.bg` Programni produkti
section). Whenever NRA publishes a new version, that mirror is
re-crawled; this README is the changelog anchor for what flows from
that mirror into the modules.
