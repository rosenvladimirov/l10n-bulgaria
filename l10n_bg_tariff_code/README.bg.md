# Bulgaria Tariff Code Management

> TARIC/HS/CN кодове + EU API

**Модул:** `l10n_bg_tariff_code` | **Версия:** 18.0.3.0.11 | **Лиценз:** LGPL-3 | **Категория:** Accounting/Localizations

## Описание

TARIC/HS/CN кодове + EU API

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `account`, `stock_delivery` | — |

**Python пакети:** `requests`

## Нови модели

- `cn_code`
- `l10n_bg.taric.cache`

## Разширени модели

- `account.move.line` (extension)
- `product.product` (extension)
- `product.template` (extension)
- `res.company` (extension)
- `res.config.settings` (extension)

## Изгледи (views)

- `views/account_move_line_views.xml`
- `views/l10n_bg_taric_cache.xml`
- `views/menu.xml`
- `views/product_template_views.xml`
- `views/res_config_view.xml`

## Заредени данни

- `data/l10n_bg_tarif_code_data.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_tariff_code' или през CLI:
odoo -i l10n_bg_tariff_code -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
