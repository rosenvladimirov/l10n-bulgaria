# ErpNet.FP — OCA IoT bridge (Community)

> ErpNet.FP ↔ OCA iot_oca bridge (Community)

**Модул:** `l10n_bg_erp_net_fp_iot_oca` | **Версия:** 18.0.11.0.0 | **Лиценз:** LGPL-3 | **Категория:** Point Of Sale

## Описание

ErpNet.FP ↔ OCA iot_oca bridge (Community)

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `iot_oca`, `mrp`, `stock` | `l10n_bg_erp_net_fp` |

## Нови модели

- `l10n.bg.packaging.weighable.mixin`
- `mrp.production`
- `stock.picking`

## Разширени модели

- `fiscal.printer.device` (extension)
- `iot.communication.system` (extension)
- `iot.device` (extension)
- `mrp.bom` (extension)
- `res.company` (extension)
- `res.config.settings` (extension)

## Изгледи (views)

- `views/fiscal_printer_device_iot_oca_bridge_views.xml`
- `views/iot_communication_system_views.xml`
- `views/iot_device_views.xml`
- `views/packaging_qc_views.xml`

## Контролери

- `controllers/main.py`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_erp_net_fp_iot_oca' или през CLI:
odoo -i l10n_bg_erp_net_fp_iot_oca -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
