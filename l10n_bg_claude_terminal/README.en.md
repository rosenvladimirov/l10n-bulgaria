# Claude Terminal (Chatter & List View)

> Claude Code terminal + AI Tokenizer (Qdrant/Ollama) — MCP Docker stack

**Module:** `l10n_bg_claude_terminal` | **Version:** 18.0.1.36.1 | **License:** AGPL-3 | **Category:** Technical

## Overview

Claude Code terminal + AI Tokenizer (Qdrant/Ollama) — MCP Docker stack

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `mail`, `web`, `bus`, `hr`, `base_setup` | — |

**External Python packages:** `pyzipper`

## New models

- `ai.composite.document`
- `ai.document.builder`
- `ai.embedding.provider`
- `ai.qdrant.client`
- `ai.view.parser`
- `ai.view.registry`
- `display_name`

## Extended models

- `ir.model` (inherited)
- `res.company` (inherited)
- `res.config.settings` (inherited)
- `res.users` (inherited)

## Views

- `views/ai_tokenizer_views.xml`
- `views/res_config_settings_views.xml`
- `views/res_users_views.xml`

## Seeded data

- `data/ai_tokenizer_cron.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_claude_terminal' or via CLI:
odoo -i l10n_bg_claude_terminal -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)
- Module tests: `tests/`

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
