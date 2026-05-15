# Payment Provider: Borica APGW (BG)

> Картови плащания през Borica APGW (EMV 3DS 2.x)

**Модул:** `payment_borica` | **Версия:** 18.0.1.0.0 | **Лиценз:** LGPL-3 | **Категория:** Accounting/Payment Providers

## Описание

Картови плащания през Borica APGW (EMV 3DS 2.x)

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `payment`, `website_payment` | — |

## Разширени модели

- `payment.provider` (extension)
- `payment.transaction` (extension)

## Изгледи (views)

- `views/payment_borica_templates.xml`
- `views/payment_provider_views.xml`

## Контролери

- `controllers/main.py`

## Заредени данни

- `data/payment_provider_data.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'payment_borica' или през CLI:
odoo -i payment_borica -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)
- Модулни тестове: `tests/`

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
