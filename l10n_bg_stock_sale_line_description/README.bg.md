# Stock Sale Line Description

> Показване на SO line description в pickings

**Модул:** `l10n_bg_stock_sale_line_description` | **Версия:** 18.0.1.0.0 | **Лиценз:** AGPL-3 | **Категория:** ?

## Описание

Показване на SO line description в pickings

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `stock`, `sale_stock` | — |

## Разширени модели

- `stock.move` (extension)

## Изгледи (views)

- `views/stock_picking_views.xml`

## Отчети (reports)

- `report/report_deliveryslip.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_stock_sale_line_description' или през CLI:
odoo -i l10n_bg_stock_sale_line_description -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
