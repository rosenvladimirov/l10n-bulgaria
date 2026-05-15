# ErpNet.FP ↔ OCA iot_oca Bridge (Community)

> CE-friendly bridge между `l10n_bg_erp_net_fp` и OCA `iot_oca`
> модула — излага ErpNet.FP везни/устройства като iot_oca системи и
> захранва packaging-weight QC. Auto-инсталира когато и двата са налични.

**Модул:** `l10n_bg_erp_net_fp_iot_oca` | **Версия:** 18.0.11.0.0 | **Лиценз:** LGPL-3 | **Категория:** Localization

## Описание

Odoo Enterprise има native `iot.box`; Community/OCA светът ползва OCA
`iot_oca`. Този bridge позволява ErpNet.FP фискалния/peripheral слой
да се интегрира с `iot_oca` на Community инсталации (Enterprise
counterpart-ът е `l10n_bg_erp_net_fp_iot`). Auto-инсталира само когато
и `l10n_bg_erp_net_fp`, и `iot_oca` са налични.

## Какво предоставя

- `action_create_matching_iot_oca_system` — регистрира ErpNet.FP
  устройство като `iot_oca` система, така че се появява в OCA IoT UI.
- `erp_net_fp_kind` Selection на iot системата — позволява на
  packaging-weight QC mixin-а да филтрира специфично за везни.
- `read_weight()` — синхронен HTTP GET към parent ErpNet.FP
  системата; публичното API, което Phase 3 packaging-weight QC
  mixin-ът (`l10n.bg.packaging.weighable.mixin`) вика за верификация
  на MO/picking тегло срещу BoM expected ± tolerance.
- `action_verify_packaging_weight` — изпълнява QC проверката.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `iot_oca`, `mrp`, `stock` | `l10n_bg_erp_net_fp` |

## Конфигурация

Auto-инсталира когато `l10n_bg_erp_net_fp` + `iot_oca` са инсталирани.
После регистрирайте ErpNet.FP везни като iot_oca системи и ползвайте
packaging-weight QC на MO-та / pickings.

## Sibling

`l10n_bg_erp_net_fp_iot` (в l10n-bulgaria-ee) е Enterprise `iot.box`
еквивалентът на този Community bridge.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Device слой: `l10n_bg_erp_net_fp`
- Enterprise еквивалент: `l10n-bulgaria-ee/l10n_bg_erp_net_fp_iot`
