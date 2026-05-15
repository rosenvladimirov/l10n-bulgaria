# Partner Multilang — Транслитерация и многоезични имена

> Автоматична кирилица→латиница транслитерация (ISO 9 / ΕΛΟΤ 743),
> езиково разпознаване, многоезично търсене на партньори и правилно
> сортиране — инфраструктурата, която прави българските partner данни
> легално съответстващи и използваеми в смесени-script бази.

**Модул:** `partner_multilang` | **Версия:** 18.0.3.0.3 | **Лиценз:** AGPL-3 | **Категория:** Localization

## Описание

Кирилските държави (България, Русия, Сърбия, Македония, Украйна,
Беларус) законово изискват латинска транслитерация на имената в
официални документи. Смесените кирилица/латиница данни също сортират
грешно в Odoo list/kanban (кирилско "Г" vs латинско "G" попадат на
различни позиции). Този модул решава и двете: транслитерира
автоматично, пази всеки превод, търси из всички тях и сортира по
езика на потребителя.

## Архитектура

### `res.transliterate.mixin` (нов AbstractModel)

Преизползваемият engine. Всеки модел, който го наследи, получава
многоезичен `display_name`:

- `_compute_display_name()` override — Odoo 18 ползва computed
  `display_name` вместо `name_get()`; този връща стойността на езика
  на потребителя, транслитерирайки on-the-fly при нужда.
- `transliterate_tracking` (Json) — записва кои полета са
  авто-транслитерирани, така че ръчните редакции не се презаписват.

### Езиково разпознаване (двустепенно)

- **Приоритет 1:** `lingua` (`LanguageDetectorBuilder`) — точен.
- **Приоритет 2:** `langdetect` — бърз fallback.

`detect_text_language(text)` избира script-а; `partner_name_translate
(name, lang, flag)` транслитерира неанглийски имена (ISO 9 за
кирилица, ΕΛΟΤ 743 за гръцки) чрез библиотеките `transliterate` +
`unidecode`.

### `res.partner` (разширен)

- `name`, `street`, `street2`, `city`, `function`, `company_name`,
  `commercial_company_name` направени `translate=True`; `name`
  получава trigram индекс за бързо многоезично търсене.
- `complete_name_multilanguage` — **JSONB колона**, добавена чрез суров
  SQL `ADD COLUMN IF NOT EXISTS`, така че техническото поле се
  материализира **без upgrade на модула**.
- `_rec_names_search()` override — търсенето match-ва всеки запазен
  превод, не само активния език.

### Други разширения

| Модел | Защо |
|---|---|
| `ir.binary` | `download_name` обработка за преводими JSONB имена (избягва счупени filenames с newlines/кирилица) |
| `res.country.state` | `name` преводимо |
| `res.lang` | sort/collation hooks |
| `res.config.settings` | `transliterate_names` фирмен toggle |

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `base`, `contacts` | — (фундаментален; без l10n зависимости) |

**Python пакети:** `transliterate`, `unidecode`, `lingua`.

## Конфигурация

1. Инсталация.
2. Settings → активирайте **Transliterate Names** (per company).
3. Съществуващите партньори се транслитерират при следващ write;
   новите при create. JSONB колоната се появява автоматично — без `-u`.

## JSONB предупреждение за downstream модули

Понеже преводимите имена живеят в PostgreSQL **JSONB** колони, всеки
модул правещ `regexp_matches` / суров SQL върху partner имена трябва
да обработва JSONB формата. Това е повтарящ се gotcha — виж
`l10n_bg_account_reconcile_patch` и `hr_org_chart_multilang_fix`,
които съществуват точно за да поправят JSONB-name обработката в
core/3rd-party код.

## Downstream consumers

`l10n_bg_multilang`, `l10n_bg_mrp_multilang`,
`l10n_bg_project_multilang`, и практически всеки отчет, който печата
partner имена двуезично.

## Известни ограничения

- Транслитерацията е rule-based (ISO 9 / ΕΛΟΤ 743); собствени имена с
  нестандартна романизация изискват ръчен override (проследен чрез
  `transliterate_tracking`).
- Езиковото разпознаване на много къси низове (1-2 знака) е ненадеждно
  — fallback към активния език.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- JSONB-fix consumers: `l10n_bg_account_reconcile_patch`, `hr_org_chart_multilang_fix`
- `readme/` — DESCRIPTION / CONTEXT изходни бележки
