# Bulgarian HR Payroll Classifications

> НКПД + КИД класификации

**Модул:** `l10n_bg_payroll_classifications` | **Версия:** 18.0.5.0.1 | **Лиценз:** LGPL-3 | **Категория:** Human Resources/Localization

## Описание

НКПД + КИД класификации

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `hr` | — |

## Нови модели

- `bg.hr.payroll.economic.activity`
- `bg.hr.payroll.ncop.classification`

## Разширени модели

- `hr.job` (extension)

## Изгледи (views)

- `views/bg_mod_economic_activity.xml`
- `views/bg_ncop_classification.xml`
- `views/hr_job_views.xml`
- `views/hr_menus.xml`

## Заредени данни

- `data/bg_hr_payroll_economic_activity`
- `data/bg_hr_payroll_ncop_classification`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_payroll_classifications' или през CLI:
odoo -i l10n_bg_payroll_classifications -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
