# AI Pipeline (Skills + Injection Engine)

> Pipeline stack with Anthropic-style Skills: progressive disclosure, semantic matching, dynamic step injection on top of AI Tokenizer.

**Module:** `l10n_bg_ai_pipeline` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Technical

## Overview

Pipeline stack with Anthropic-style Skills: progressive disclosure, semantic matching, dynamic step injection on top of AI Tokenizer.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| — | `l10n_bg_claude_terminal` |

## New models

- `ai.pipeline.run`
- `ai.pipeline.runner`
- `ai.pipeline.step`
- `ai.qdrant.skills.client`
- `ai.skill`
- `display_name`

## Extended models

- `ai.composite.document` (inherited)
- `ai.qdrant.client` (inherited)

## Views

- `views/ai_pipeline_run_views.xml`
- `views/ai_pipeline_step_views.xml`
- `views/ai_skill_views.xml`
- `views/menu.xml`

## Seeded data

- `data/pipeline_steps.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_ai_pipeline' or via CLI:
odoo -i l10n_bg_ai_pipeline -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)
- Module tests: `tests/`

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
