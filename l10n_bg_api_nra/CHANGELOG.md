# Changelog

All notable changes to **l10n_bg_api_nra** are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and the project adheres to [Semantic Versioning](https://semver.org/).

## [19.0.1.3.0] - 2026-07-07

### Added
- Overridable document-type seam on `nra.api.provider`:
  `_get_service_doc_type`, `_get_file_doc_type`, `_get_file_type`. The defaults
  read the existing module-level dicts (behaviour unchanged for d1/d6/etz), but
  a plug-in declaration type can now contribute its NRA codes by overriding
  these instead of mutating the module dicts (used by `l10n_bg_api_nra_saft` to
  source the SAF-T codes from system parameters).

### Changed
- `submit_declaration` resolves service/file document types via the new seam
  methods instead of reading the module dicts directly. Backward-compatible.
