# Bulgaria localization Configuration

> Централна конфигурация на българската локализация

**Модул:** `l10n_bg_config` | **Версия:** 18.0.8.3.0 | **Лиценз:** LGPL-3 | **Категория:** Localization

## Описание

Централна конфигурация на българската локализация

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `account`, `base_vat` | `l10n_bg`, `l10n_bg_ledger`, `l10n_bg_tariff_code` |

**Python пакети:** `xmltodict`, `cryptography`

## Нови модели

- `account.move`
- `account.move.line`
- `l10n.bg.config.mixin`
- `res.partner`

## Разширени модели

- `account.account.tag` (extension)
- `account.chart.template` (extension)
- `ir.module.module` (extension)
- `res.bank` (extension)
- `res.company` (extension)
- `res.config.settings` (extension)
- `res.country` (extension)

## Изгледи (views)

- `views/account_account_tag_views.xml`
- `views/account_move_views.xml`
- `views/partner_view.xml`
- `views/res_company_views.xml`
- `views/res_config_view.xml`

## Контролери

- `controllers/blacklist_controller.py`

## Заредени данни

- `data/blacklist.enc`
- `data/res_lang_data.xml`
- `data/template`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'l10n_bg_config' или през CLI:
odoo -i l10n_bg_config -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
