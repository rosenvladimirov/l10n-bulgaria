# AI Pipeline — Skills + Injection Engine

> A pipeline stack with Anthropic-style **Skills**: progressive
> disclosure, semantic matching and dynamic step injection, layered on
> the AI Tokenizer (Qdrant) from `l10n_bg_claude_terminal`.

**Module:** `l10n_bg_ai_pipeline` | **Version:** 18.0.1.0.0 | **License:** AGPL-3 | **Category:** Localization / AI

## Overview

A reusable execution framework for AI-assisted document processing.
Instead of one monolithic prompt, work is decomposed into **skills**
(self-contained capabilities) selected by semantic matching against
the task, with steps injected dynamically — the "progressive
disclosure" pattern: only the skills relevant to the current document
are loaded into context.

## Data model

| Model | Role |
|---|---|
| `ai.skill` | A named capability with a description embedding + language scope (`all` handles `[xx_YY]…[/xx_YY]` language blocks) |
| `ai.pipeline.step` | One step definition in a pipeline |
| `ai.pipeline.run` | Audit trail for one execution of a named pipeline |
| `ai.pipeline.runner` | Orchestrates step execution + dynamic injection |
| `ai.composite.document` | A document assembled across steps |
| `ai.qdrant.skills.client` (AbstractModel) | Qdrant REST client for the **skills** embeddings collection — kept separate so skill-description vectors never mix with document vectors |

Semantic matching: a task's embedding is compared against skill
description embeddings in Qdrant; the top matches are injected as the
active step set.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| (via base) | `l10n_bg_claude_terminal` (AI Tokenizer / Qdrant / Ollama infra) |

## Configuration

1. Install `l10n_bg_claude_terminal` first (provides Qdrant/Ollama
   connection config on the company).
2. Install this module; define `ai.skill` records (description drives
   the semantic match) and assemble pipelines from `ai.pipeline.step`.

## Downstream consumers

`l10n_bg_ai_invoice_glue` (vendor-bill extraction) and
`l10n_bg_ai_customs_glue` (customs-declaration extraction) run their
extraction as pipelines/skills on this engine.

## Known limitations

- Quality of skill selection depends on well-written skill
  descriptions (they are the embedding source).
- Requires a reachable Qdrant + embedding model (Ollama) via
  `l10n_bg_claude_terminal`.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Infra: `l10n_bg_claude_terminal`
- Consumers: `l10n_bg_ai_invoice_glue`, `l10n_bg_ai_customs_glue`
