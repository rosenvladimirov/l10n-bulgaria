# Claude Terminal + AI Tokenizer

> In-Odoo Claude Code terminal plus the AI Tokenizer (Qdrant vector
> store + Ollama embeddings) that backs semantic search and the AI
> pipeline — an MCP Docker stack integration.

**Module:** `l10n_bg_claude_terminal` | **Version:** 18.0.1.36.1 | **License:** AGPL-3 | **Category:** Localization / AI

## Overview

This is the AI infrastructure layer for the localization. It provides
two things:

1. **Claude Code terminal** — an interactive Claude session surfaced
   inside Odoo (chatter / list-view integration), backed by an MCP
   Docker stack.
2. **AI Tokenizer** — a Qdrant vector store fed by Ollama embeddings,
   so any module can tokenize records and do semantic similarity
   search. `l10n_bg_ai_pipeline` builds its skill engine on top of
   this.

Its very high minor version (18.0.1.36.1) reflects long, active
iteration — it is the most-evolved AI module in the stack.

## Key model

`ai.qdrant.client` — Qdrant REST client. Reads connection config from
the company: `claude_qdrant_url`, `claude_qdrant_api_key` (system-group
protected), `claude_qdrant_collection_prefix`. The API key field is
`groups="base.group_system"` and accessed via `sudo()`.

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `mail`, `web`, `bus`, `hr`, `base_setup` | (foundational AI infra; no l10n deps) |

## Configuration

1. Settings (company) → set `claude_qdrant_url`,
   `claude_qdrant_api_key`, collection prefix; configure the Ollama
   embedding endpoint.
2. Deploy the MCP Docker stack the terminal connects to (see
   `claude.ai/memory/server_base_install_vm_docker.md` for the
   infra recipe).

## Downstream consumers

`l10n_bg_ai_pipeline` (skills engine), and any module doing semantic
record search / AI tokenization.

## Known limitations

- Requires external services (Qdrant, Ollama, MCP stack) reachable
  from Odoo; it is an integration layer, not self-contained.
- The Claude terminal is operator-facing tooling, not an end-user
  business feature.

## See also

- Parent repo overview: [`../OVERVIEW.md`](../OVERVIEW.md)
- Builds on this: `l10n_bg_ai_pipeline`
- Infra recipe: `claude.ai/memory/server_base_install_vm_docker.md`
