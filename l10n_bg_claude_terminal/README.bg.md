# Claude Terminal + AI Tokenizer

> In-Odoo Claude Code терминал плюс AI Tokenizer (Qdrant vector store +
> Ollama embeddings), който захранва семантичното търсене и AI
> pipeline — MCP Docker стек интеграция.

**Модул:** `l10n_bg_claude_terminal` | **Версия:** 18.0.1.36.1 | **Лиценз:** AGPL-3 | **Категория:** Localization / AI

## Описание

Това е AI инфраструктурният слой на локализацията. Предоставя две неща:

1. **Claude Code терминал** — интерактивна Claude сесия, показана
   вътре в Odoo (chatter / list-view интеграция), backed от MCP
   Docker стек.
2. **AI Tokenizer** — Qdrant vector store, захранван от Ollama
   embeddings, така че всеки модул може да tokenize-ва записи и да
   прави семантично similarity търсене. `l10n_bg_ai_pipeline` строи
   своя skill engine върху това.

Много високата минорна версия (18.0.1.36.1) отразява дълга, активна
итерация — това е най-развитият AI модул в стека.

## Ключов модел

`ai.qdrant.client` — Qdrant REST клиент. Чете connection config от
фирмата: `claude_qdrant_url`, `claude_qdrant_api_key` (system-group
protected), `claude_qdrant_collection_prefix`. API key полето е
`groups="base.group_system"` и се достъпва през `sudo()`.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `mail`, `web`, `bus`, `hr`, `base_setup` | (фундаментална AI инфра; без l10n зависимости) |

## Конфигурация

1. Settings (фирма) → задайте `claude_qdrant_url`,
   `claude_qdrant_api_key`, collection prefix; конфигурирайте Ollama
   embedding endpoint.
2. Деплойнете MCP Docker стека, към който терминалът се свързва (виж
   `claude.ai/memory/server_base_install_vm_docker.md` за инфра рецептата).

## Downstream consumers

`l10n_bg_ai_pipeline` (skills engine) и всеки модул, правещ
семантично record търсене / AI tokenization.

## Известни ограничения

- Изисква външни услуги (Qdrant, Ollama, MCP стек), достъпни от Odoo;
  това е integration слой, не self-contained.
- Claude терминалът е operator-facing tooling, не end-user бизнес feature.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Надгражда това: `l10n_bg_ai_pipeline`
- Инфра рецепта: `claude.ai/memory/server_base_install_vm_docker.md`
