# България — SO line описание върху pickings

> Показва описанието на реда от поръчката върху складовите pickings и
> delivery slip-овете, така че текстът на доставения артикул да съвпада
> с поръчаното от клиента.

**Модул:** `l10n_bg_stock_sale_line_description` | **Версия:** 18.0.1.0.0 | **Лиценз:** AGPL-3 | **Категория:** Localization

## Описание

По подразбиране delivery slip-ът показва името на продукта, не
описателния текст, който търговецът е въвел на реда на поръчката.
Българските клиенти очакват документът за доставка да носи същата
формулировка като поръчката. Този модул показва SO line описанието на
формата на picking-а и delivery-slip отчета.

## Какво прави

- Наследява `stock.view_picking_form` — добавя SO line описанието до
  `description_picking` в operations page.
- Наследява `stock.report_delivery_document` (и serial-move-line
  варианта) — печата описанието в move таблицата.

Само report/view-layer — без model полета.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `sale_stock` | `l10n_bg` |

## Конфигурация

Няма. Инсталирайте — описанието следва от поръчката върху picking-а и
печатния delivery slip.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Свързани: `l10n_bg_report_stock`, `l10n_bg_stock_picking_comment_template`
