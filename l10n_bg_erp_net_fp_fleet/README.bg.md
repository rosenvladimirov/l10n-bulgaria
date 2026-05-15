# ErpNet.FP Fleet Manager

> Централен control plane за разпределени ErpNet.FP proxy инстанции:
> HMAC-signed heartbeat enrolment, Fernet-криптирани shared secrets,
> pairing токени и command queue.

**Модул:** `l10n_bg_erp_net_fp_fleet` | **Версия:** 18.0.1.0.0 | **Лиценз:** LGPL-3 | **Категория:** Localization

## Описание

Търговец с много обекти пуска много ErpNet.FP proxy инстанции (по
една на локация, близо до фискалните устройства). Този модул е
**централният registry + control plane**: proxy-тата се enrol-ват
сами, изпращат HMAC-signed heartbeats и получават команди през queue
— така че оператор управлява целия fleet от един Odoo instance вместо
да пипа всяка кутия.

## Архитектура

- **Enrolment**: public-facing registry endpoints; proxy се enrol-ва
  с pairing токен, после се издава long-lived shared secret.
- **Heartbeats**: proxy-то изпраща периодични heartbeats, чието body
  е HMAC-signed с неговия shared secret; сървърът валидира HMAC-а за
  автентикация на proxy-то.
- **Съхранение на secret**: shared secrets са **Fernet-криптирани at
  rest** (AES-128-CBC + HMAC-SHA256) с ключа в `ir.config_parameter`
  `l10n_bg_erp_net_fp_fleet.fernet_key` (auto-created;
  `erpnet.fp.fernet` модел прави encrypt/decrypt). DB-backup leak сам
  по себе си не разкрива fleet secrets.
- **Lifecycle actions**: `action_generate_pairing_token`,
  `action_reset_secret`, `action_archive_proxy`.
- **Command queue**: pull-model — proxy-тата poll-ват за queued
  команди и репортват completion.

## Зависимости

| Odoo базови | Българска локализация | Python пакет |
|---|---|---|
| `base`, `mail` | — (control plane; работи с `l10n_bg_erp_net_fp` на proxy страната) | `cryptography` |

## Конфигурация

1. Инсталирайте; Fernet ключът auto-генерира при първа употреба.
2. Генерирайте pairing токен per proxy → конфигурирайте proxy-то с него.
3. Proxy-то се enrol-ва, получава secret-а си и започва HMAC
   heartbeats; управлявайте го от fleet view (reset secret / archive
   при нужда).

## Известни ограничения

- HMAC валидацията итерира candidate secrets — отбелязано като бавно
  при много голям fleet мащаб (приемливо за типични merchant fleets).
- Това е сървърната страна; proxy страната живее в ErpNet.FP
  deployment-а, не в Odoo.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Device интеграция: `l10n_bg_erp_net_fp`
