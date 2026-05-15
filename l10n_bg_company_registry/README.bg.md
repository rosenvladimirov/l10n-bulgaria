# Bulgarian Company Registry Integration

> Интеграция с Търговския регистър

**Модул:** `l10n_bg_company_registry` | **Версия:** 18.0.2.0.2 | **Лиценз:** LGPL-3 | **Категория:** Localization

## Описание

Интеграция с Търговския регистър

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `contacts` | `l10n_bg_config`, `l10n_bg_city` |

**Python пакети:** `requests`

## Разширени модели

- `res.partner` (extension)

## Изгледи (views)

- `views/res_partner_views.xml`

## Помощници (wizards)

- `wizard/bg_company_search_wizard.py`

## Заредени данни

- `data/ir_actions_server.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_company_registry' или през CLI:
odoo -i l10n_bg_company_registry -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
