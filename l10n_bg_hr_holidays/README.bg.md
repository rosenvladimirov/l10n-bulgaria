# Bulgaria - HR Holidays

> Български типове отпуски (61) по КТ и НЗОК

**Модул:** `l10n_bg_hr_holidays` | **Версия:** 18.0.1.4.0 | **Лиценз:** LGPL-3 | **Категория:** Human Resources/Time Off

## Описание

Български типове отпуски (61) по КТ и НЗОК

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `hr_contract`, `hr_holidays` | `l10n_bg` |

## Нови модели

- `hr.leave.balance`
- `nssi.leave.reason`

## Разширени модели

- `hr.leave` (extension)
- `hr.leave.allocation` (extension)
- `hr.leave.type` (extension)

## Изгледи (views)

- `views/hr_leave_balance_views.xml`
- `views/hr_leave_schedule_views.xml`
- `views/hr_leave_type_views.xml`
- `views/hr_leave_views.xml`
- `views/l10n_bg_nssi_leave_reason.xml`

## Заредени данни

- `data/hr_holidays_data.xml`
- `data/hr_holidays_doo_treatment.xml`
- `data/nssi.leave.reason.csv`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_hr_holidays' или през CLI:
odoo -i l10n_bg_hr_holidays -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
