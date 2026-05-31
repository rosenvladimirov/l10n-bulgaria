# HR Org Chart — Multilang JSONB поправка

> Резолва преводимите JSONB имена на служители до plain strings преди
> `hr_org_chart` widget-ът да ги рендира — без това org chart-ът
> показва сурови `{"en_US": ...}` dict-ове.

**Модул:** `hr_org_chart_multilang_fix` | **Версия:** 18.0.1.0.0 | **Лиценз:** AGPL-3 | **Категория:** Localization

## Описание

Когато `partner_multilang` / `l10n_bg_multilang` направят
`hr.employee.name` преводимо, Odoo 18 го съхранява като PostgreSQL
**JSONB** колона. `hr_org_chart` OWL widget-ът получава суровия JSONB
dict и го рендира буквално (`{"en_US": "...", "bg_BG": "..."}`)
вместо името. Тази поправка резолва стойността до plain string за
активния език преди да достигне JavaScript слоя.

## Какво прави

Override-ва `_prepare_employee_data` и резолва всяко name-like поле от
JSONB форма до active-language string. Ако multilang модулите не са
инсталирани (без JSONB), поправката е **no-op** — безопасно за
инсталация независимо.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `hr_org_chart` | (ефективен само с `l10n_bg_multilang`/`partner_multilang`) |

## Конфигурация

Няма. Инсталирайте — org chart-ът рендира правилни имена.

## Свързани JSONB-fix модули

Това е един от JSONB-name compatibility shim-ове; другият е
`l10n_bg_account_reconcile_patch` (поправя JSONB имена в
bank-statement reconciliation). Виж `partner_multilang` за root cause.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Root cause: `partner_multilang` (JSONB имена)
