# Claude Terminal (Chatter & List View)

> Claude Code терминал + AI Tokenizer

**Модул:** `l10n_bg_claude_terminal` | **Версия:** 18.0.1.36.1 | **Лиценз:** AGPL-3 | **Категория:** Technical

## Описание

Claude Code терминал + AI Tokenizer

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `mail`, `web`, `bus`, `hr`, `base_setup` | — |

**Python пакети:** `pyzipper`

## Нови модели

- `ai.composite.document`
- `ai.document.builder`
- `ai.embedding.provider`
- `ai.qdrant.client`
- `ai.view.parser`
- `ai.view.registry`
- `display_name`

## Разширени модели

- `ir.model` (extension)
- `res.company` (extension)
- `res.config.settings` (extension)
- `res.users` (extension)

## Изгледи (views)

- `views/ai_tokenizer_views.xml`
- `views/res_config_settings_views.xml`
- `views/res_users_views.xml`

## Заредени данни

- `data/ai_tokenizer_cron.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_claude_terminal' или през CLI:
odoo -i l10n_bg_claude_terminal -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)
- Модулни тестове: `tests/`

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
