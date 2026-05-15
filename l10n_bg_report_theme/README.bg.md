# Bulgaria - Report Theme Sections

> Корпоративен report theme — section-based layout

**Модул:** `l10n_bg_report_theme` | **Версия:** 18.0.5.2.0 | **Лиценз:** LGPL-3 | **Категория:** ?

## Описание

Корпоративен report theme — section-based layout

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `web`, `sale`, `account`, `stock`, `purchase` | `l10n_bg_config` |

**Python пакети:** `webcolors`

## Разширени модели

- `base.document.layout` (extension)
- `ir.actions.report` (extension)
- `res.company` (extension)

## Изгледи (views)

- `views/base_document_layout_views.xml`
- `views/ir_action_report_templates.xml`
- `views/purchase_order_templates.xml`
- `views/purchase_quotation_templates.xml`
- `views/report_invoice.xml`
- `views/report_templates.xml`
- `views/res_company_views.xml`

## Заредени данни

- `data/report_layout.xml`
- `data/report_paperformat_data.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_report_theme' или през CLI:
odoo -i l10n_bg_report_theme -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
