# L10n Bg Report Stock

> Приемно-предавателни документи в stock picking

**Модул:** `l10n_bg_report_stock` | **Версия:** 18.0.1.0.0 | **Лиценз:** AGPL-3 | **Категория:** ?

## Описание

Приемно-предавателни документи в stock picking

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `stock` | `l10n_bg_report_theme` |

## Разширени модели

- `stock.move.line` (extension)

## Отчети (reports)

- `report/report_accepted_deliveryslip.xml`
- `report/report_handover_protocol.xml`
- `report/stock_report_views.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_report_stock' или през CLI:
odoo -i l10n_bg_report_stock -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
