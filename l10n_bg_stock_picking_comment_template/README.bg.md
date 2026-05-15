# България — Позициониране на comment-template върху picking

> Препозиционира top/bottom блоковете на `base_comment_template` върху
> българския приемно-предавателен протокол и документ, така че
> търговският текст да попадне там, където BG layout-ът го очаква.

**Модул:** `l10n_bg_stock_picking_comment_template` | **Версия:** 18.0.1.0.0 | **Лиценз:** AGPL-3 | **Категория:** Localization

## Описание

OCA `base_comment_template` инжектира стандартен top/bottom търговски
текст в отчетите, но неговите default anchor точки не съвпадат с
българския приемно-предавателен / accepted-delivery layout от
`l10n_bg_report_stock`. Този модул re-anchor-ва тези comment блокове
към правилните позиции на BG документите.

## Какво прави

Наследява `stock.report_delivery_document`:

- `<xpath expr="//div[@id='informations']" position="after">` — top
  comment блок след info блока
- `<xpath expr="//div[@name='signature']" position="before">` —
  bottom comment блок преди signature зоната

Layout-aware чрез guards (`is_handover_protocol`,
`l10n_bg_report_stock_accepted`), така че препозиционира само на
релевантните BG документи, не на generic delivery slip-а.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `stock`, `base_comment_template` | `l10n_bg`, `l10n_bg_report_stock` |

## Конфигурация

Няма. Инсталирайте заедно с `l10n_bg_report_stock` и
`base_comment_template`; comment блоковете се рендират на правилното
място на BG handover/accepted-delivery документите.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Документи: `l10n_bg_report_stock`
