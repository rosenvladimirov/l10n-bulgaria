# Платежен доставчик — Borica APGW

> Приемане на картови плащания през Borica e-commerce gateway (APGW,
> CGI v4.0, EMV 3-D Secure 2.x) — acquiring канал, издаван от
> български банки.

**Модул:** `payment_borica` | **Версия:** 19.0.1.0.0 | **Лиценз:** LGPL-3 | **Категория:** Localization / Payment

## Описание

Borica е националният картов оператор на България; неговият **APGW**
(e-commerce gateway) е acquiring каналът, който повечето български
банки издават на търговците. Този модул добавя Borica като Odoo
`payment.provider`, така че web-shop / invoice плащания минават през
gateway-а на банката с пълна EMV 3-D Secure 2.x автентикация на
картодържателя.

## Архитектура

- `payment.provider` — `provider` selection разширен с
  `("borica", "Borica APGW")`; носи terminal/acquirer credentials на
  търговеца.
- CGI v4.0 request signing + 3DS 2.x redirect flow.
- Контролерът `/payment/borica/return` проверява P_SIGN с публичния
  сертификат на Борика (невалиден подпис → 403) и подава данните на
  `_process`; транзакцията се намира по `ORDER` (`borica_order`, 6 цифри
  от id), а `_apply_updates` задава състоянието (платено / отказано /
  чака).

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `payment` | — |

## Конфигурация

1. Invoicing → Payment Providers → Borica APGW → въведете
   bank-issued terminal ID / acquirer credentials, задайте test/production.
2. Активирайте на website / invoice payment flow-овете.
3. Верифицирайте, че gateway callback URL-ът е достъпен от Borica.

## Стратегическа бележка

Borica + myPOS са primary card-acceptance доставчиците за българската
локализация (LGPL-3, EU фокус). Виж
`claude.ai/memory/project_payment_provider_strategy.md`.

## Известни ограничения

- Изисква Borica merchant договор през българска банка
  (terminal/acquirer credentials са bank-issued).
- 3DS challenge UX зависи от издаващата банка на картодържателя.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Sibling доставчик: `payment_mypos`
- Стратегия: `claude.ai/memory/project_payment_provider_strategy.md`
