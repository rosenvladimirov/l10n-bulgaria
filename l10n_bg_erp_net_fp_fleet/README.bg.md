# ErpNet.FP Fleet Manager

> Централен fleet manager за ErpNet.FP инстанции

**Модул:** `l10n_bg_erp_net_fp_fleet` | **Версия:** 18.0.1.0.0 | **Лиценз:** LGPL-3 | **Категория:** Hardware/Fleet

## Описание

Централен fleet manager за ErpNet.FP инстанции

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `mail` | — |

**Python пакети:** `cryptography`

## Нови модели

- `erpnet.fp.fernet`
- `erpnet.fp.proxy`
- `name`

## Изгледи (views)

- `views/erpnet_fp_proxy_views.xml`
- `views/menu_items.xml`

## Помощници (wizards)

- `wizard/erpnet_fp_program_vat_wizard.py`

## Контролери

- `controllers/registry.py`

## Заредени данни

- `data/ir_config_parameter.xml`
- `data/ir_cron.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_erp_net_fp_fleet' или през CLI:
odoo -i l10n_bg_erp_net_fp_fleet -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
