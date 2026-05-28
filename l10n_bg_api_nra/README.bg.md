# България — НАП API интеграция (ядро)

> Гръбнакът за подаване на декларации към Националната агенция за
> приходите (НАП) през публичното ѝ API, с подписване с
> квалифициран електронен подпис (КЕП) в браузъра.

**Модул:** `l10n_bg_api_nra` | **Версия:** 18.0.1.4.2 | **Лиценз:** LGPL-3 | **Категория:** Accounting/Localizations | **Приложение:** Да (самостоятелно НАП приложение)

## Описание

`l10n_bg_api_nra` е transport + signing ядрото, върху което всеки
специфичен декларационен модул (Д1, Д6, ДДС, VIES, ЕТЗ, Наредба Н-18
е-магазин) се изгражда. Притежава HTTP клиента, превключването
test/production endpoint, споделянето на access token през wallet и
client-side КЕП signing диалога. Съдържанието/форматът на
декларациите живее в съседните `l10n_bg_api_nra_*` и
`l10n_bg_hr_payroll_nra_*` модули; този модул доставя подписания
payload до НАП и обратно.

Регистриран е като **самостоятелно Odoo приложение** (собствено root
меню + НАП векторна икона), а не скрит под Счетоводство.

## Архитектура

### `nra.api.provider`

Суровият HTTP клиент.

- `_get_base_url()` — чете `ir.config_parameter`
  `l10n_bg_api_nra.base_url` (fallback към вградения НАП API base).
- `_get_submit_endpoint(company)` — резолва пълния submit URL спрямо
  **test vs production** режима на фирмата, така че същият код път
  работи срещу НАП sandbox или live без редакции.
- Endpoint path константите се добавят към резолвнатия base.

### `nra.declaration` (абстрактен родител) + конкретни декларации

| Модел | Декларация |
|---|---|
| `nra.declaration` | споделена state машина + submit/poll plumbing |
| `nra.declaration.d1` (+ `.d1.line`) | Декларация Образец 1 |
| `nra.declaration.d6` (+ `.d6.line`) | Декларация Образец 6 |
| `nra.declaration.vat` (+ `.vat.line`) | ДДС декларация |
| `nra.declaration.vies` | VIES декларация |
| `nra.declaration.h18_eshop` (+ `.h18.line`, `.h18.line.art`, `.h18.refund`) | Наредба Н-18 регистър продажби е-магазин (`action_collect_h18_orders`, `action_h18_generate_xml`) |

XSD схемите се доставят в `data/xsd/` и валидират payload-ите преди подаване.

### Споделяне на token през wallet (`res.users`)

НАП access токените не се пазят per-user в чист текст. **Owner**-ът на
токена (`company.l10n_bg_nra_token_user_id`) държи ключа
`nra_access_token` в своя `l10n_bg_bank_wallet`. Когато друг
потребител подава, модулът копира ключа от wallet-а на owner-а в
wallet-а на действащия потребител (пропуска ако потребителят Е
owner-ът, и първо чисти stale ключове). Така екип може да подава
декларации без всеки член да държи суровите credentials.

### Client-side КЕП подписване

`static/src/js/kep_signer.js` + `sign_submit_dialog.js` +
`sign_submit_widget.js` (+ QWeb `sign_submit_dialog.xml`)
имплементират flow-а за квалифициран електронен подпис **в браузъра**
— частният ключ никога не напуска клиента. `controllers/main.py`
обработва sign/submit round-trip endpoints.

### Разширени модели

| Модел | Добавка |
|---|---|
| `res.company` | `l10n_bg_nra_token_user_id` (owner на токена) + test/prod режим |
| `res.users` | wallet token-copy логика при submit |
| `hr.employee` | `_l10n_bg_nra_declaration_lookups`, `action_view_l10n_bg_nra_declarations` |

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| (accounting/HR база) | `l10n_bg_config`, `l10n_bg_bank_wallet` |

`l10n_bg_bank_wallet` е задължителен — там живее криптираният НАП
access token.

## Конфигурация

1. Инсталация (регистрира НАП приложението + иконата).
2. Settings → задайте test/production НАП режима на фирмата и
   `l10n_bg_nra_token_user_id` (owner на credential-ите).
3. Owner-ът на токена се автентикира веднъж; неговият wallet пази
   access токена. Другите потребители го наследяват прозрачно при submit.
4. (Опционално) override `l10n_bg_api_nra.base_url` в
   `ir.config_parameter` за custom/sandbox gateway.

## Downstream consumers

`l10n_bg_api_nra_dec1`, `_dec6`, `_etz`, `_vat`, `_noi*`,
`l10n_bg_hr_payroll_nra_*`, `l10n_bg_account_nra_vat` — всички
делегират transport + signing тук.

## Известни ограничения

- Token sharing предполага един credential owner на фирма;
  multi-owner ротация е ръчна.
- КЕП подписването изисква browser-side signing разширение/драйвер на
  клиентската машина.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- НАП формат справки: `claude.ai/memory/reference_nra_obr55_okd5_formats.md`
- Cross-repo карта: `claude.ai/L10N_BG_ECOSYSTEM.md`

---

## Roadmap — Покритие на НАП и НОИ декларации

**Източник:** 30 официални НАП XSD схеми (2025/2026 batch) обхващат
10 тематики на деклaриране. Сравнението с този каталог дава едно
място на истината за това какво е имплементирано, какво е частично
и какво остава.

### Легенда

| Символ | Значение |
|--------|----------|
| ✅ | Production-ready: backend + XML build + XSD валидация + UI |
| ⚠️ | Частично: XSD е импортнат, но XML build трябва rewrite, или `declaration_type` extension е TODO |
| ❌ | Не е стартирано: XSD е наличен, няма Odoo модул |
| ⛔ | Извън обхват: специализиран домейн, преднамерено не имплементирано |

### Матрица на имплементацията

| # | Тематика | XSD файл(ове) | Модул | Статус |
|---|----------|---------------|-------|--------|
| 1 | **Декларация Обр.1** (данни за осигуреното лице, месечно) | CSV формат (без XSD) | `l10n_bg_api_nra_dec1` + `l10n_bg_hr_payroll_nra_dec1` | ✅ |
| 2 | **Декларация Обр.6** (агрегирани месечни вноски) | Без публичен XSD | `l10n_bg_api_nra_dec6` + `l10n_bg_hr_payroll_nra_noi` | ✅ |
| 3 | **ЕТЗ чл.62 КТ** (стандартно уведомление за ТД) | `etz_employ_restrict.xsd` | `l10n_bg_api_nra_etz` + `l10n_bg_hr_payroll_nra_etz` | ✅ |
| 4 | **ЕТЗ чл.123 ал.5 КТ** (правоприемство на работодател) | `etz_123_employer.xsd` | XSD копиран в `l10n_bg_api_nra_etz/data/`; `declaration_type='etz123'` **TODO** | ⚠️ |
| 5 | **Справка чл.73 ал.1 ЗДДФЛ** (доходи извън трудови) | `SPR73_1.xsd` (root `<dec731>`) | `l10n_bg_api_nra_spr73` | ✅ |
| 6 | **Справка чл.73 ал.6 ЗДДФЛ** (доходи от трудови, годишна) | `dec73_6_publish.xsd` | `l10n_bg_api_nra_spr73` (XML build е reconstructed; **rewrite срещу XSD-то — TODO**) | ⚠️ |
| 7 | **ДДС Декларация + дневници** (месечен ZIP package) | Без публичен XSD (CSV формат) | `l10n_bg_api_nra_vat` + `l10n_bg_account_nra_vat` (поддържа per-file КЕП подписване) | ✅ |
| 8 | **Приложение №9 НОИ** (болничен лист) | `Pril9.xsd` | `l10n_bg_api_nssi_pril9` | ✅ |
| 9 | **Приложение №10 НОИ** (майчинство, от осигурител) | `Pril10.xsd` | `l10n_bg_api_nssi_pril10` | ✅ |
| 10 | **Приложение №11 НОИ** (майчинство, самоосигуряващи се) | `Pril11.xsd` | `l10n_bg_api_nssi_pril11` | ✅ |
| 11 | **Уведомление чл.77 ДОПК** (закриване/преобразуване) | Без XSD (хартиено/PDF) | `l10n_bg_dopk_art77` (QWeb PDF wizard за образец `ОКд-107`) | ✅ |
| 12 | **Интрастат** (ЕС стоки/услуги) | Без публичен XSD | `l10n_bg_intrastat` (XML генериране, без XSD валидация) | ⚠️ |
| 13 | **SAF-T** (Standard Audit File for Tax) | `BG_SAFT_Schema_V_1.0.2.xsd` (активна от 01.01.2026), `V_1.0` (legacy) | — | ❌ |
| 14 | **ГДД чл.92 ЗКПО** (годишна данъчна декларация юр.лица) | `dec92_2024_public.xsd` | — | ❌ |
| 15 | **Превози със стоки с висок фискален риск (СВФР)** | `decHfr_internal/import/export/thirdcountry_v5_restrict.xsd`, `API_decHfr_annul/confirm_v3_restrict.xsd` (общо 6 схеми) | — | ❌ |
| 16 | **Е-магазини алтернативен режим** (Наредба Н-18) | `dec_audit.xsd` | — | ❌ |
| 17 | **Фискални устройства мониторинг (FDmon)** — 16 XSD | `fbdata*.xsd`, `nra{common,req,res}.xsd`, `r{chng,dereg,reg}.xsd`, `req31/res31.xsd`, `xtask/ztask/xtiasutd/ztiasutd.xsd` | — | ⛔ специализирано |
| 18 | **Пощенски оператори, данни чл.25 ЗНАП** — 4 XSD | `pos_25.xsd`, `pos_25_tpacc.xsd`, `trans_25.xsd`, `trans_25_tbpos.xsd` | — | ⛔ специализирано |

### План за изпълнение

Планът е разделен на три фази: **довършване на започната работа**,
**активна опашка за разработка** (изпълнява се в строг ред) и
**извън обхват** специализирани области.

#### Фаза A — Довършване на започната работа (immediate)

Тези items имат backend модели или импортнати XSD-та вече налични;
завършват се преди да започне нов модул.

| # | Item | Модул | Effort |
|---|------|-------|--------|
| A1 | **Rewrite на Справка чл.73 ал.6 XML** срещу `dec73_6_publish.xsd` — backend моделът съществува, но XML build е reconstructed от спецификационни документи; aligne към официалния XSD. | `l10n_bg_api_nra_spr73` (update) | 2–3 човеко-дни |
| A2 | **ЕТЗ чл.123 declaration type** — добави `declaration_type='etz123'` selection на `nra.declaration` с по-кратката 13-полева схема. Свързва се с уведомление чл.77 ДОПК при правоприемство. XSD вече е импортнат. | `l10n_bg_api_nra_etz` (update) | 1–2 човеко-дни |

#### Фаза B — Активна опашка за разработка (строг ред)

Всеки модул започва само след като предишният е production-ready.
SAF-T е преднамерено в края, за да консолидира опита от
по-ранните модули; статутният му ефект (01.01.2026) се проследява
отделно като hard deadline.

| # | Ред | Item | Модул | Effort | Бележки |
|---|-----|------|-------|--------|---------|
| B1 | 1-ви | **Е-магазини алтернативен режим** | `l10n_bg_eshop_alt` (нов) | 2–3 човеко-дни | Произвежда `dec_audit.xsd` за онлайн магазини без СУПТО; най-малка повърхност, доставя се пръв, за да валидира modular pattern за нови declaration types. |
| B2 | 2-ри | **Фискални устройства мониторинг (FDmon)** | `l10n_bg_erp_net_fp_fdmon` (нов) | 10–15 човеко-дни | 16 XSD-та за комуникация НАП↔фискално устройство. Отделен POS bridge (`l10n_bg_erp_net_fp_iot`) съществува, но говори друг protocol stack. |
| B3 | 3-ти | **Годишна данъчна декларация чл.92 ЗКПО** | `l10n_bg_api_nra_dec92` (нов) | 7–10 човеко-дни | Всяко юридическо лице подава до 30 юни за предходната отчетна година. Source: GL + `l10n_bg_reports_audit`. |
| B4 | 4-ти | **СВФР — стоки с висок фискален риск** | `l10n_bg_svfr` (нов) | 3–5 човеко-дни | 6 XSD + REST API за внос / износ / вътрешен / трета страна / анулиране / потвърждение. За търговци на едро / превозвачи на горива, текстил, мобилни устройства и др. |
| B5 | 5-ти | **SAF-T (Standard Audit File for Tax)** | `l10n_bg_saf_t` (нов) | 7–10 човеко-дни | Месечни / годишни / on-demand XML-и от `account.move.line` + product/partner/tax метаданни. Имплементира се последен, за да консолидира patterns от B1–B4. Заповед З-ЦУ-30-1247/25.08.2025 влиза в сила от 01.01.2026 с прогресивни прагове — този deadline се проследява извън тази опашка. |

#### Фаза C — Извън обхват (не имплементирай освен при изрично изискване)

| Item | Причина |
|------|---------|
| **Пощенски оператори чл.25 ЗНАП** — 4 XSD | Специализиран домейн (само пощенски оператори и агенти за паричен превод); не е част от стандартния payroll / tax / audit workflow. 5–7 човеко-дни ако някога потрябва. |

### Workflow за нови XSD imports

При интегриране на нов XSD:

1. Слагай файла под `static/description/` (или `data/` за backward
   compatibility) на съответния модул за декларация.
2. Generate-ни sample XML; валидирай с
   `xmllint --noout --schema /path/to/schema.xsd /tmp/sample.xml`.
3. Ако element имената не съвпадат с reconstructed, XSD-то е авторитет —
   rewrite-ни `_build_*_xml()` метода, не override-вай схемата.
4. Добави `_validate_*_xsd()` метод, който ползва
   `lxml.etree.XMLSchema`, така че генерирането прилага схемата по време
   на изпълнение.
5. Re-тест срещу НАП client-side софтуера (към момента v17.03+ за
   доходни справки; v20250603 за FDmon; и т.н.) преди да третираш
   модула като production-ready.

### Източник на истината

30-XSD каталогът, ползван за този gap analysis, е извън репозиторията
(private mirror, crawled от секцията Програмни продукти на `nra.bg`).
Когато НАП публикува нова версия, mirror-ът се обхожда отново; този
README е changelog anchor за това какво от mirror-а минава в модулите.
