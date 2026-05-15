# Bulgaria - Cities and Locations

> ЕКАТТЕ — населени места, общини, кметства, области

**Модул:** `l10n_bg_city` | **Версия:** 18.0.1.1.0 | **Лиценз:** AGPL-3 | **Категория:** Localization

## Описание

ЕКАТТЕ — населени места, общини, кметства, области

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `base_address_extended`, `contacts` | — |

**Python пакети:** `dbfread`, `requests`

## Нови модели

- `l10n.bg.ekatte.sync`
- `res.city.types`

## Разширени модели

- `res.city` (extension)
- `res.country.state` (extension)

## Изгледи (views)

- `views/l10n_bg_ekatte_sync_views.xml`
- `views/res_city_view.xml`

## Заредени данни

- `data/ir_cron_data.xml`
- `data/res.city.cityhall.csv`
- `data/res.city.csv`
- `data/res.city.municipality.csv`
- `data/res.country.state.csv`
- `data/res_city_types.xml`
- `data/res_country_data.xml`
- `data/src`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_city' или през CLI:
odoo -i l10n_bg_city -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
