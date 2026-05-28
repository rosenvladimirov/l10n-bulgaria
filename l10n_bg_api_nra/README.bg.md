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

### Приоритизиран план

**P0 — задължително за общо съответствие в отчетен цикъл 2025/2026**

1. **Rewrite на XML build за Справка чл.73 ал.6** срещу `dec73_6_publish.xsd`
   - Модул: `l10n_bg_api_nra_spr73` (само update)
   - Защо: backend моделът съществува, но XML build е базиран на
     reconstructed имена от спецификационни документи; нагласа към
     официалния XSD е задължителна преди подаване в НАП.
   - Estimate: 2–3 човеко-дни.

2. **SAF-T модул** (`l10n_bg_saf_t`, нов)
   - Trigger: Заповед З-ЦУ-30-1247/25.08.2025 въвежда SAF-T от
     **01 януари 2026** за големи предприятия (с по-нататъшни прагове).
   - Защо: законово изискване; не може да се замени от съществуващи
     audit reports.
   - Estimate: 7–10 човеко-дни за месечни/годишни/on-demand XML-и от
     `account.move.line` + product/partner/tax метаданни.

3. **Годишна данъчна декларация чл.92 ЗКПО** (`l10n_bg_api_nra_dec92`, нов)
   - Trigger: Чл.92 ЗКПО — всяко юридическо лице подава до 30 юни за
     предходната отчетна година.
   - Source: GL + audit reports (`l10n_bg_reports_audit`).
   - Estimate: 7–10 човеко-дни.

4. **ЕТЗ чл.123 declaration type** (`etz123` в съществуващ модул)
   - Trigger: вървят заедно с уведомление чл.77 ДОПК при правоприемство.
   - Backend: отделна Selection стойност `declaration_type='etz123'`
     на `nra.declaration` с по-кратката 13-полева схема.
   - Estimate: 1–2 човеко-дни (XSD вече е импортнат).

**P1 — реализация само ако бизнес моделът на конкретна инсталация
го изисква**

5. **СВФР (стоки с висок фискален риск)** — за търговци на едро / превозвачи на
   горива, текстил, мобилни устройства и др. Нов модул `l10n_bg_svfr` с 6 XSD
   и REST API интеграция към НАП. 3–5 човеко-дни.

6. **Е-магазини алтернативен режим** — за онлайн магазини без фискално
   устройство (СУПТО). Нов модул `l10n_bg_eshop_alt` с `dec_audit.xsd`.
   2–3 човеко-дни.

**P2 — извън обхват освен при специфично направление**

7. **Фискални устройства мониторинг (FDmon)** — за производители /
   дистрибутори на фискални устройства. Има отделен модул
   `l10n_bg_erp_net_fp_iot` за POS интеграция; FDmon е друг protocol
   stack. 10–15 човеко-дни.

8. **Пощенски оператори чл.25 ЗНАП** — само за пощенски оператори и
   агенти за паричен превод. 5–7 човеко-дни.

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
