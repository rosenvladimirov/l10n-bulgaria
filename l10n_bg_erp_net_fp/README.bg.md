# България — ErpNet.FP фискални принтери

> Browser-to-printer печат на фискални бонове за български POS през
> ErpNet.FP сървър, с PLU управление, external-POS shift обработка и
> самостоятелен shift dashboard.

**Модул:** `l10n_bg_erp_net_fp` | **Версия:** 18.0.15.1.0 | **Лиценз:** LGPL-3 | **Категория:** Localization

## Описание

Българското законодателство изисква фискални бонове от регистрирано
фискално устройство. Този модул свързва Odoo POS с български фискални
принтери през **ErpNet.FP** сървъра: бонът се печата **директно от
браузъра към устройството**, заобикаляйки backend bottlenecks, докато
backend-ът все още управлява административните операции (Z/X отчети,
cash in/out). Българските данъчни групи (А, Б, В, Г) се мапват
автоматично, а печатът пада до стандартен бон при грешка на
устройството, така че продажба никога не се блокира.

## Модел на данните (ключови entities)

| Модел | Роля |
|---|---|
| `fiscal.printer.device` | Регистрирано ErpNet.FP устройство + статуса му |
| `fiscal.printer.status` / `.status.history` | Live + историческо здраве на устройството (`action_request_status`, cleanup, history view) |
| `fiscal.printer.response` | Per-request response log (по `request_id`) |
| `fiscal.frame.log` | Суров fiscal-frame request/response одит trail |
| `fiscal.plu` | **PLU (Price Look-Up)** артикули — name+price snapshot синхронизиран от POS pricelist; consistency check преди push |
| `fiscal.shift` / `.shift.receipt` | External-POS-mode shift + боновете му |
| `fiscal.z.report` | Z-отчет запис (`action_test_z_report`, close) |
| `fiscal.session` | Z-cycle session маркер |

### PLU обработка

`fiscal.plu` огледалва POS pricelist артикулите в паметта на
устройството. `action_check_consistency` / `action_sync_from_pricelist`
/ `action_push_to_device` поддържат device PLU-тата подравнени;
`_next_free_plu` разпределя слотове (max ~10000). Mid-shift промяна на
цена маркира PLU stale → re-push при следващ shift open (виж
`claude.ai/memory/reference_fiscal_plu_concept.md`).

### External POS режим

За setup-и, при които продажбите произлизат извън стандартен
`pos.session` (`fiscal_printer_device_external`,
`pos_session_external`): `action_pos_session_open`,
`action_pos_session_closing_control`, `_l10n_bg_import_receipts`,
`action_l10n_bg_external_push_retry`,
`action_l10n_bg_external_force_close`. **Самостоятелен OWL dashboard**
се сервира на route `/external-shift` (собствен asset bundle +
`controllers/external_shift.py`).

### POS / product разширения

`pos.config`, `pos.order`, `pos.session`, `pos.payment.method`,
`pos.printer` разширени за фискалния поток; `product.template/product`
+ `product.pricelist` разширени за PLU linkage; `account.tax.group`
мапнат към А/Б/В/Г.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `point_of_sale` (+ account) | `l10n_bg` |

## Конфигурация

1. Вдигнете ErpNet.FP сървър, достъпен от касиерските браузъри.
2. Settings → регистрирайте `fiscal.printer.device` записи (host/port).
3. Мапнете POS configs към устройства; верифицирайте А/Б/В/Г мапинга.
4. Синхронизирайте PLU от pricelist и push към устройството.
5. За external режим: ползвайте `/external-shift` dashboard.

## Sister модули

- `l10n_bg_erp_net_fp_fleet` — централен fleet manager за много ErpNet.FP инстанции
- `l10n_bg_erp_net_fp_iot_oca` (CE/OCA) / `l10n_bg_erp_net_fp_iot` (EE) — Odoo IoT-box bridges

## Известни ограничения

- Директният browser→device печат изисква ErpNet.FP service-ът да е
  достъпен от всяка касиерска машина.
- PLU device капацитетът е краен (~10000); големи каталози изискват
  curation кои продукти се PLU-push-ват.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- PLU concept: `claude.ai/memory/reference_fiscal_plu_concept.md`
- `readme/` — DESCRIPTION изходни бележки
