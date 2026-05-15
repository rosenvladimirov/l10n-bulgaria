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
