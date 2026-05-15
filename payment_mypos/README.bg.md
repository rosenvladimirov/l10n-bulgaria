# Платежен доставчик — myPOS Checkout

> Приемане на картови плащания през myPOS Checkout API (REST + 3DS):
> hosted-redirect purchase плюс refund/void.

**Модул:** `payment_mypos` | **Версия:** 18.0.2.0.0 | **Лиценз:** LGPL-3 | **Категория:** Localization / Payment

## Описание

myPOS е общоевропейски merchant-acquiring доставчик, популярен сред
българските SMB (хардуерът му е споделена линия с Datecs). Този модул
добавя myPOS като Odoo `payment.provider` ползвайки **myPOS Checkout
API v1.4.1** — hosted-redirect purchase flow (`IPCPurchase`) за
плащане, плюс `IPCRefund` / `IPCVoid` за post-payment операции.

## Архитектура

- `payment.provider` — myPOS доставчик с Checkout credentials.
  Refund/void изискват допълнителни credentials (зададени на
  доставчика) — задължителни за `IPCRefund` / `IPCVoid` под Checkout
  API v1.4.1.
- Purchase: hosted-redirect (`IPCPurchase`) с 3-D Secure.
- Refund/Void: server-to-server REST calls по ключ оригиналната
  транзакция.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `payment` | `l10n_bg` |

## Конфигурация

1. Invoicing → Payment Providers → myPOS → въведете Checkout
   store/keys; добавете refund/void credentials ако ви трябват
   server-side reversals.
2. Задайте test/production; активирайте на website/invoice flow-овете.

## AUP / compliance ограничения

Според myPOS Acceptable Use Policy: PAN/PIN/CVV никога не трябва да
се логват или съхраняват; refund само към оригиналната карта;
chargeback rate под 1%; pre-auth позволен само за hotel / cruise /
rent-a-car. Виж
`claude.ai/memory/reference_mypos_acceptable_use_policy.md`.

## Стратегическа бележка

myPOS + Borica са primary card доставчиците за локализацията (EU
фокус, LGPL-3). Виж
`claude.ai/memory/project_payment_provider_strategy.md`.

## Известни ограничения

- Refund/void изискват допълнителните Checkout credentials
  конфигурирани; иначе само purchase работи.
- Hosted-redirect UX е myPOS-controlled.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Sibling доставчик: `payment_borica`
- AUP: `claude.ai/memory/reference_mypos_acceptable_use_policy.md`
