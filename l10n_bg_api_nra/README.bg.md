# Bulgaria - NRA API Integration

> API интеграция с НАП за подаване на декларации

**Модул:** `l10n_bg_api_nra` | **Версия:** 18.0.1.4.2 | **Лиценз:** LGPL-3 | **Категория:** Accounting/Localizations/Bulgaria

## Описание

API интеграция с НАП за подаване на декларации

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `mail`, `hr` | `l10n_bg_config`, `l10n_bg_bank_wallet` |

**Python пакети:** `requests`, `lxml`

## Нови модели

- `nra.api.provider`
- `nra.declaration`
- `nra.declaration.d1.line`
- `nra.declaration.d6.line`
- `nra.declaration.h18.line`
- `nra.declaration.h18.line.art`
- `nra.declaration.h18.refund`
- `nra.declaration.vat.line`
- `nra.declaration.vies.line`

## Разширени модели

- `hr.employee` (extension)
- `nra.declaration` (extension)
- `res.company` (extension)
- `res.users` (extension)

## Изгледи (views)

- `views/hr_employee_views.xml`
- `views/menu.xml`
- `views/nra_declaration_h18_views.xml`
- `views/nra_declaration_views.xml`
- `views/res_company_views.xml`

## Контролери

- `controllers/main.py`

## Заредени данни

- `data/nra_data.xml`
- `data/xsd`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_api_nra' или през CLI:
odoo -i l10n_bg_api_nra -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
