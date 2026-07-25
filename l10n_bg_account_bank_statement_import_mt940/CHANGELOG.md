# Changelog

All notable changes to the l10n_bg_account_bank_statement_import_mt940 module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [16.0.1.0.0] - 2026-03-21

### Added
- Initial release: MT940 bank statement import for Odoo Enterprise (backport from 18.0)
- Ported from 18.0 `l10n_bg_account_bank_statement_import_mt940` to work with 16.0 Enterprise `account_bank_statement_import`
- Extends `account.journal._parse_bank_statement_file()` (EE chain of responsibility pattern)
- Registers "MT940" in `_get_bank_statements_available_import_formats()`
- Bulgarian bank parsers: ProCredit (PRCBBGSF), UniCredit Bulbank (UNCRBGSF), UBB (UBBSBGSF)
- Multi-encoding support: UTF-8, Windows-1251, ISO-8859-5
- Unique import ID generation with MD5 hash to prevent duplicates
- mt940 library StatementNumber pattern patch for ProCredit compatibility

*Assisted by Claude Code*
