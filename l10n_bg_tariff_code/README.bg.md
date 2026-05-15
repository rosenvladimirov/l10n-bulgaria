# България — Управление на TARIC / HS / CN кодове

> Управление на митнически стокови кодове за продукти и фактурни
> редове, с локален кеш на ЕС TARIC тарифни ставки, изтеглени от
> европейския CIRCABC dataset.

**Модул:** `l10n_bg_tariff_code` | **Версия:** 18.0.3.0.11 | **Лиценз:** LGPL-3 | **Категория:** Localization

## Описание

Българските митнически декларации и Intrastat отчетност изискват
всеки продукт да носи своя **TARIC / HS / CN** стоков код, а
митническата оценка се нуждае от приложимата тарифна ставка.
Заявка към ЕС TARIC системата на всеки ред би била бавна и
rate-limited, затова този модул поддържа **локален кеш на ставки** по
ключ CN код + държава + период на валидност, опресняван от
официалните CIRCABC данни.

## Модел на данните

### `l10n_bg.taric.cache` (нов)

Локален кеш на TARIC тарифни ставки от CIRCABC.

| Поле | Значение |
|---|---|
| `cn_code` | Combined Nomenclature код (rec name) |
| `country_code` | Държава на произход, за която важи ставката |
| `measure_type` | TARIC measure тип (мито, anti-dumping, …) |
| `valid_from` / `valid_to` | Период на валидност на ставката |

Lookup-ите удрят кеша първо; miss (или stale запис след `valid_to`)
тригерира refresh от конфигурираното TARIC API.

### Разширени модели

| Модел | Добавка |
|---|---|
| `product.template` / `product.product` | TARIC/HS/CN code полета |
| `account.move.line` | tariff code propagation за митническа оценка |
| `res.company` | `l10n_bg_taric_api_url`, `l10n_bg_taric_api_enabled`, `l10n_bg_taric_cache_duration` (часове), default fallback ставка, auto-download toggle |
| `res.config.settings` | излага горните като settings |

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `product` (+ account база) | `l10n_bg` |

**Python пакети:** `requests`.

## Конфигурация

1. Settings → Bulgarian Localization → TARIC:
   - **Enable TARIC API** + **TARIC API URL** (ЕС endpoint).
   - **Cache Duration (hours)** — колко дълго cached ставка се доверява.
   - Default fallback ставка когато код не може да се резолва.
2. Задайте TARIC/CN кодове на продуктите (ръчно или чрез
   `taric_ai_classifier` за AI-подпомогната класификация).

## Downstream consumers

`taric_ai_classifier` (AI класификацията записва кодове тук),
`l10n_bg_intrastat` (стокови кодове на декларации),
`l10n_bg_tax_admin` митнически потоци.

## Известни ограничения

- Свежестта на кеша зависи от `cache_duration`; ставка, която се
  промени в средата на прозореца, се взема едва след изтичане (или
  ръчен refresh).
- CIRCABC dataset структурата се променя понякога — fetch слоят
  толерира чести промени, но голяма ЕС формат промяна изисква code update.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- AI класификатор: `taric_ai_classifier`
- Митнически consumer: `l10n_bg_intrastat`, `l10n_bg_tax_admin`
