# Partner Multilang

> Многоезични имена на партньори + транслитерация

**Модул:** `partner_multilang` | **Версия:** 18.0.3.0.3 | **Лиценз:** AGPL-3 | **Категория:** Localization

## Описание

Многоезични имена на партньори + транслитерация

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `contacts` | — |

**Python пакети:** `transliterate`, `unidecode`, `lingua`

## Нови модели

- `raw`
- `res.company`
- `res.partner`
- `res.transliterate.mixin`

## Разширени модели

- `ir.binary` (extension)
- `res.config.settings` (extension)
- `res.country.state` (extension)
- `res.lang` (extension)

## Изгледи (views)

- `views/res_config_settings_view.xml`
- `views/res_lang_views.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'partner_multilang' или през CLI:
odoo -i partner_multilang -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
