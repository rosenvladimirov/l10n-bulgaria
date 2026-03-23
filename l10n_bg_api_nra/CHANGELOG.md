# Changelog

All notable changes to the l10n_bg_api_nra module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.1.0.0] - 2026-03-23

### Added
- NRA Public API client (`nra.api.provider`) — OAuth 2.0 client credentials grant, rate limiting with exponential backoff, automatic token refresh
- Base declaration model (`nra.declaration`) with full workflow: draft → ready → submitted → accepted / partially accepted / rejected / error
- XML generation and XSD validation framework with `_build_xml_tree()` / `_validate_xml()` extension points
- Declaration Form 1 (Декларация обр. 1) — insured persons data with insurance types, contributions (DOO, ZO, DZPO), income tax
- Declaration Form 6 (Декларация обр. 6) — due contributions and income tax per payment type with auto-computed totals
- Electronic Labor Records / ЕТЗ (Електронни трудови записи) — contract registration, correction, deletion with NKPD position codes and termination grounds
- VAT Declaration (ДДС декларация) — cell-based structure with auto-computed VAT due / refund amounts
- VIES Declaration (VIES декларация) — intra-community supplies, services, and triangular operations with auto-computed totals per operation type
- NRA API credentials stored encrypted in `l10n_bg_bank_wallet` crypto wallet (Fernet + PBKDF2)
- Credential setup wizard (`nra.credentials.wizard`) — passwords entered via transient model, never stored in database
- Token distribution at login — copies NRA API key, secret, and access token to authenticated user's wallet (`res_users._nra_distribute_credentials`)
- Dual-strategy credential retrieval — current user's wallet first, token owner's wallet fallback for cron jobs
- Company-level NRA API configuration with test mode toggle and connection test button
- Security groups: NRA Declarations User (view/create) and NRA Declarations Manager (full access + API config)
- Multi-company record rule on declarations
- Sequences per declaration type: D1/, D6/, ETZ/, VAT/, VIES/ prefixes with yearly numbering
- System parameters for configurable API base URL, token endpoint, and timeout
- Full menu structure under Accounting → NRA Declarations (НАП) with sub-menus: Insurance, Labor Records, Tax
- List/form/search views with status badges, conditional tabs per declaration type, and XML download
- Chatter integration (mail.thread, mail.activity.mixin) with field tracking on key state changes
