# България — Приемно-предавателни складови документи

> Добавя българския приемно-предавателен протокол и accepted-delivery
> slip PDF отчети към складовите pickings.

**Модул:** `l10n_bg_report_stock` | **Версия:** 18.0.1.0.0 | **Лиценз:** AGPL-3 | **Категория:** Localization

## Описание

Българските движения на стоки се документират с **приемно-предавателен
протокол** и **приемно-предавателен документ** — подписано
доказателство за доставка/приемане, различно от фактурата. Този модул
добавя тези два PDF отчета към `stock.picking` ползвайки
section-based `l10n_bg_report_theme` layout-а.

## Какво предоставя

- `report/report_accepted_deliveryslip.xml` — приемно-предавателен документ
- `report/report_handover_protocol.xml` — приемно-предавателен протокол
- `report/stock_report_views.xml` — свързва отчетите към picking-а
- `stock.move.line._get_aggregated_product_quantities()` разширен, така
  че документите агрегират количествата по българския начин

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `stock` | `l10n_bg`, `l10n_bg_report_theme` |

## Конфигурация

Няма. Инсталирайте — двата отчета се появяват в Print менюто на
складовите pickings.

## Свързани модули

- `l10n_bg_stock_picking_comment_template` — препозиционира
  base_comment_template блокове на тези документи
- `l10n_bg_stock_sale_line_description` — добавя SO line description
- `l10n_bg_sale_order_delivery_note` — SO-side accepted-delivery отчет

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Report theme: `l10n_bg_report_theme`
