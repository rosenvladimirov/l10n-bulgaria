# Bulgarian Sale Order Delivery Note

> Acceptance/Delivery doc за SO

**Модул:** `l10n_bg_sale_order_delivery_note` | **Версия:** 18.0.1.1.1 | **Лиценз:** LGPL-3 | **Категория:** Sales/Bulgaria

## Описание

Acceptance/Delivery doc за SO

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `sale`, `base_comment_template` | `l10n_bg_report_theme` |

## Нови модели

- `sale.order`

## Отчети (reports)

- `report/ir_action_report_templates.xml`
- `report/ir_actions_report.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_sale_order_delivery_note' или през CLI:
odoo -i l10n_bg_sale_order_delivery_note -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
