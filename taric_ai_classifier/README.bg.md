# AI TARIC & INTRASTAT Classifier

> AI (Claude) — автоматична TARIC класификация

**Модул:** `taric_ai_classifier` | **Версия:** 18.0.2.0.0 | **Лиценз:** LGPL-3 | **Категория:** Accounting/Localizations

## Описание

AI (Claude) — автоматична TARIC класификация

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `product`, `stock`, `stock_delivery`, `account`, `ai_agent_core` | — |

## Нови модели

- `taric.classification.history`
- `taric.code`

## Разширени модели

- `product.template` (extension)
- `res.config.settings` (extension)

## Изгледи (views)

- `views/product_views.xml`
- `views/res_config_settings_views.xml`
- `views/taric_code_views.xml`

## Помощници (wizards)

- `wizard/taric_classify_wizard.py`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'taric_ai_classifier' или през CLI:
odoo -i taric_ai_classifier -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
