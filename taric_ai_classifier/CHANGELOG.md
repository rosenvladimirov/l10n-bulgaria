# Changelog

All notable changes to the taric_ai_classifier module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.2.0.0] - 2026-03-22

### Changed
- **BREAKING:** Replaced direct Anthropic API calls with `ai_agent_core` module
- `search_by_ai()` now creates `ai.agent.request` and invokes Claude Code CLI via the core module
- Removed `anthropic_api_key` from settings — API credentials managed by `ai_agent_core`
- Removed `requests` external dependency — no longer needed
- Added `ai_agent_core` to module dependencies

### Removed
- Direct HTTP calls to `api.anthropic.com` from `taric_code.py`
- `anthropic_api_key` field from `res.config.settings`
- `requests` from `external_dependencies`

*Assisted by Claude Code*

## [18.0.1.0.2] - 2026-03-01

### Added
- Initial changelog entry
