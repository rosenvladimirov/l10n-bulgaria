# Multi Language Partner, Company, Employee

> Многоезична поддръжка за Partner/Company/Employee

**Модул:** `l10n_bg_multilang` | **Версия:** 18.0.0.1.0 | **Лиценз:** LGPL-3 | **Категория:** Localization

## Описание

Многоезична поддръжка за Partner/Company/Employee

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `hr`, `stock`, `partner_multilang` | `partner_multilang` |

## Нови модели

- `hr.employee`
- `res.country.state`

## Разширени модели

- `res.bank` (extension)
- `res.currency` (extension)
- `resource.resource` (extension)
- `stock.warehouse` (extension)

## Изгледи (views)

- `views/res_country_view.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_multilang' или през CLI:
odoo -i l10n_bg_multilang -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
