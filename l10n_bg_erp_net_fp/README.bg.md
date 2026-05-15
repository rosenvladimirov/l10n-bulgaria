# ErpNet.FP Fiscal Printer for odoo

> ErpNet.FP фискални принтери

**Модул:** `l10n_bg_erp_net_fp` | **Версия:** 18.0.15.1.0 | **Лиценз:** LGPL-3 | **Категория:** Point Of Sale

## Описание

ErpNet.FP фискални принтери

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `bus`, `mail`, `point_of_sale`, `account` | — |

## Нови модели

- `fiscal.frame.log`
- `fiscal.printer.device`
- `fiscal.printer.response`
- `fiscal.printer.status`
- `fiscal.session`
- `l10n.bg.fiscal.plu`
- `l10n.bg.fiscal.shift`
- `l10n.bg.fiscal.shift.receipt`
- `l10n.bg.fiscal.shift.receipt.line`
- `l10n.bg.fiscal.z.report`
- `receipt_number`
- `request_id`
- `summary`

## Разширени модели

- `account.tax.group` (extension)
- `fiscal.printer.device` (extension)
- `pos.config` (extension)
- `pos.order` (extension)
- `pos.payment.method` (extension)
- `pos.printer` (extension)
- `pos.session` (extension)
- `product.pricelist` (extension)
- `product.pricelist.item` (extension)
- `product.product` (extension)
- `product.template` (extension)
- `res.config.settings` (extension)
- `res.users` (extension)

## Изгледи (views)

- `views/account_tax_views.xml`
- `views/external_shift_layout.xml`
- `views/fiscal_frame_log_views.xml`
- `views/fiscal_plu_views.xml`
- `views/fiscal_printer_device_proxy_views.xml`
- `views/fiscal_printer_device_views.xml`
- `views/fiscal_printer_response_views.xml`
- `views/fiscal_session_views.xml`
- `views/fiscal_shift_receipt_views.xml`
- `views/fiscal_shift_views.xml`
- `views/fiscal_z_report_views.xml`
- `views/grafana_settings_views.xml`
- `views/grafana_views.xml`
- `views/menu_items.xml`
- `views/menu_items_proxy.xml`
- `views/pos_config_proxy_views.xml`
- `views/pos_config_view.xml`
- `views/pos_order_view.xml`
- `views/pos_payment_method_proxy_views.xml`
- `views/pos_printer_views.xml`
- `views/pos_session_view.xml`
- `views/product_template_proxy_views.xml`
- `views/res_config_settings_views.xml`
- `views/res_users_views.xml`

## Помощници (wizards)

- `wizard/fiscal_cash_operation_wizard.py`
- `wizard/plu_allocate_wizard.py`
- `wizard/plu_push_wizard.py`
- `wizard/plu_topn_wizard.py`
- `wizard/x_report_wizard.py`

## Контролери

- `controllers/external_shift.py`
- `controllers/main.py`

## Заредени данни

- `data/fiscal_printer_device_cron.xml`
- `data/proxy_sequences.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_erp_net_fp' или през CLI:
odoo -i l10n_bg_erp_net_fp -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
