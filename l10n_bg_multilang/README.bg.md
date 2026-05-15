# България — Многоезични core записи

> Разширява transliteration engine-а на `partner_multilang` отвъд
> партньорите към служители, банки, складове, валути, ресурси и
> области — така че всеки запис, който се печата на български
> документ, да е двуезичен.

**Модул:** `l10n_bg_multilang` | **Версия:** 18.0.0.1.0 | **Лиценз:** LGPL-3 | **Категория:** Localization

## Описание

`partner_multilang` прави `res.partner` имената многоезични + авто
транслитерирани. Но български фактура/ТРЗ документ също печата имена
на служители, банки, складове и валутни етикети — те се нуждаят от
същото двуезично третиране. Този модул прилага
`res.transliterate.mixin` и `translate=True` към този по-широк набор
core модели.

## Разширени модели

| Модел | Преводими поле(та) | Mixin |
|---|---|---|
| `hr.employee` | `name` | + `res.transliterate.mixin` |
| `res.country.state` | `name` | + `res.transliterate.mixin` |
| `res.bank` | `name` | — |
| `stock.warehouse` | `name` | — |
| `res.currency` | `symbol`, `currency_unit_label`, `currency_subunit_label` | — |
| `resource.resource` | `name` | — |
| `res.country` | (преводими hooks) | — |

Служител и country-state получават пълния transliteration mixin (авто
кирилица→латиница + многоезичен `display_name`); останалите получават
`translate=True`, за да могат стойностите да се поддържат per език и
да се печатат коректно на документи/отчети.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| (hr/stock/resource база) | `partner_multilang` |

Твърда зависимост от `partner_multilang` — transliteration engine-ът
и JSONB-name инфраструктурата живеят там.

## Конфигурация

Без конфигурация. След инсталация изброените модели приемат
per-език стойности; транслитерацията следва фирмения toggle на
`partner_multilang` (**Transliterate Names**).

## Защо отделен модул

Държан отделно от `partner_multilang`, за да не принуждава
deployment, който се нуждае само от многоезични *партньори* (напр.
чист sales setup), да превежда HR/stock/resource модели, които не печата.

## Известни ограничения

- Наследява всички `partner_multilang` caveats (JSONB-name обработка
  за суров SQL, разпознаване на къси низове).
- `res.currency` label превод засяга само display; счетоводните суми
  не са засегнати.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Engine: `partner_multilang`
- Sibling разширения: `l10n_bg_mrp_multilang`, `l10n_bg_project_multilang`
