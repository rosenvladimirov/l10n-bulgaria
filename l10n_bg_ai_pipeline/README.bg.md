# AI Pipeline — Skills + Injection Engine

> Pipeline стек с Anthropic-style **Skills**: progressive disclosure,
> семантично съвпадение и динамично инжектиране на стъпки, надграден
> върху AI Tokenizer (Qdrant) от `l10n_bg_claude_terminal`.

**Модул:** `l10n_bg_ai_pipeline` | **Версия:** 18.0.1.0.0 | **Лиценз:** AGPL-3 | **Категория:** Localization / AI

## Описание

Преизползваема execution рамка за AI-подпомогната обработка на
документи. Вместо един монолитен prompt, работата се декомпозира на
**skills** (самостоятелни способности), избирани чрез семантично
съвпадение спрямо задачата, с динамично инжектирани стъпки —
"progressive disclosure" pattern-ът: само релевантните за текущия
документ skills се зареждат в контекста.

## Модел на данните

| Модел | Роля |
|---|---|
| `ai.skill` | Именувана способност с description embedding + language scope (`all` обработва `[xx_YY]…[/xx_YY]` езикови блокове) |
| `ai.pipeline.step` | Дефиниция на една стъпка в pipeline |
| `ai.pipeline.run` | Одит trail за едно изпълнение на именуван pipeline |
| `ai.pipeline.runner` | Оркестрира step изпълнение + динамично инжектиране |
| `ai.composite.document` | Документ, сглобен през стъпки |
| `ai.qdrant.skills.client` (AbstractModel) | Qdrant REST клиент за **skills** embeddings колекцията — отделен, така че skill-description векторите никога не се смесват с документните вектори |

Семантично съвпадение: embedding на задачата се сравнява срещу skill
description embeddings в Qdrant; топ-съвпаденията се инжектират като
активния step набор.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| (през base) | `l10n_bg_claude_terminal` (AI Tokenizer / Qdrant / Ollama инфра) |

## Конфигурация

1. Инсталирайте `l10n_bg_claude_terminal` първо (предоставя
   Qdrant/Ollama connection config на фирмата).
2. Инсталирайте този модул; дефинирайте `ai.skill` записи
   (description движи семантичния match) и сглобете pipelines от
   `ai.pipeline.step`.

## Downstream consumers

`l10n_bg_ai_invoice_glue` (vendor-bill извличане) и
`l10n_bg_ai_customs_glue` (customs-declaration извличане) изпълняват
своето извличане като pipelines/skills на този engine.

## Известни ограничения

- Качеството на skill selection зависи от добре написани skill
  descriptions (те са embedding източникът).
- Изисква достъпен Qdrant + embedding модел (Ollama) през
  `l10n_bg_claude_terminal`.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Инфра: `l10n_bg_claude_terminal`
- Consumers: `l10n_bg_ai_invoice_glue`, `l10n_bg_ai_customs_glue`
