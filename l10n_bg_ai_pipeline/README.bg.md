# AI Pipeline (Skills + Injection Engine)

> AI pipeline стек със скилове (progressive disclosure)

**Модул:** `l10n_bg_ai_pipeline` | **Версия:** 18.0.1.0.0 | **Лиценз:** AGPL-3 | **Категория:** Technical

## Описание

AI pipeline стек със скилове (progressive disclosure)

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| — | `l10n_bg_claude_terminal` |

## Нови модели

- `ai.pipeline.run`
- `ai.pipeline.runner`
- `ai.pipeline.step`
- `ai.qdrant.skills.client`
- `ai.skill`
- `display_name`

## Разширени модели

- `ai.composite.document` (extension)
- `ai.qdrant.client` (extension)

## Изгледи (views)

- `views/ai_pipeline_run_views.xml`
- `views/ai_pipeline_step_views.xml`
- `views/ai_skill_views.xml`
- `views/menu.xml`

## Заредени данни

- `data/pipeline_steps.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_ai_pipeline' или през CLI:
odoo -i l10n_bg_ai_pipeline -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)
- Модулни тестове: `tests/`

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
