# Payment Provider: myPOS

> Картови плащания през myPOS Checkout API

**Модул:** `payment_mypos` | **Версия:** 18.0.1.2.0 | **Лиценз:** LGPL-3 | **Категория:** Accounting/Payment Providers

## Описание

Картови плащания през myPOS Checkout API

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `payment`, `website_payment` | — |

## Разширени модели

- `payment.provider` (extension)
- `payment.transaction` (extension)

## Изгледи (views)

- `views/payment_mypos_templates.xml`
- `views/payment_provider_views.xml`

## Контролери

- `controllers/main.py`

## Заредени данни

- `data/payment_provider_data.xml`

## Инсталация

```bash
# Добавете пътя на репозиторията в Odoo addons_path,
# след това инсталирайте през UI Apps → търсене 'payment_mypos' или през CLI:
odoo -i payment_mypos -d <вашата_база> --stop-after-init
```

## Свързани

- Главно репозитори: [`l10n-bulgaria`](../README.md)
- Модулни тестове: `tests/`

---
*Генериран 2026-05-15 от `__manifest__.py` + source layout. Ръчно обогатяване за пълен handbook.*
