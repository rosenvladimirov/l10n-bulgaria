# България — Account Reconcile JSONB-Name поправка

> Patch-ва bank-statement reconciliation, така че partner matching-ът
> работи когато partner имената са съхранени като преводим JSONB
> (страничен ефект от `partner_multilang`).

**Модул:** `l10n_bg_account_reconcile_patch` | **Версия:** 18.0.1.0.0 | **Лиценз:** OPL-1 | **Категория:** Localization

## Описание

Когато `partner_multilang` направи `res.partner.name` преводима
**JSONB** колона, Odoo bank-statement reconciliation partner-matching
изпълнява `regexp_matches` срещу суровия JSONB и не намира партньора.
Този модул monkey-patch-ва matching логиката да резолва JSONB името
първо, така че auto-reconciliation продължава да работи в многоезична
база.

## Какво прави

Чрез `post_load_hook` (monkey-patch, без model промени):

- `_retrieve_partner_patch` — заменя partner-retrieval логиката;
  SQL `regexp_matches(...)` сега оперира върху резолвнатия текст на
  името вместо JSONB blob-а.
- `_get_st_line_strings_for_matching` — настроен, така че
  statement-line низовете сравняват срещу правилната name репрезентация.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `account_accountant` (reconcile) | ефективен с `partner_multilang` |

## Конфигурация

Няма. Инсталирайте — reconciliation partner matching толерира JSONB имена.

## Свързани JSONB-fix модули

Companion на `hr_org_chart_multilang_fix` (org-chart JSONB имена).
Root cause документиран в `partner_multilang`.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- Root cause: `partner_multilang`
