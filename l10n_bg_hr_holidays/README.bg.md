# България — Отпуски по КТ (61 типа)

> Пълният български каталог типове отпуски по Кодекса на труда (КТ) и
> НЗОК: платен годишен, болнични, майчинство/бащинство, учебни,
> граждански дълг — с НОИ reason кодове, DOO третиране, pro-rata
> разпределение и годишен график-планер.

**Модул:** `l10n_bg_hr_holidays` | **Версия:** 18.0.1.4.0 | **Лиценз:** LGPL-3 | **Категория:** Human Resources/Time Off

## Описание

Odoo доставя generic time-off модел; българската ТРЗ изисква
**61-те законови типа отпуски** с техните легални кодове, 17-те НЗОК
болнични reason кода и осигурителното третиране, което всеки тип
получава (намалява ли ден DOO базата? за сметка на работодателя ли е?).
Този модул доставя всичко това като data + model слой, който
payroll модулите консумират.

## Модел на данните

### `hr.leave.type` (разширен)

| Поле | Предназначение |
|---|---|
| `l10n_bg_code` | Законов код, напр. `155` (платен годишен, КТ чл. 155-157), `163` (майчинство). Управлява display name `[код] име` и downstream филтриране |
| `l10n_bg_allow_paid_days` | Маркира типове, при които важат дни за сметка на работодателя |
| `l10n_bg_leave_reason_id` | M2O → `nssi.leave.reason` |
| `l10n_bg_doo_treatment` | Selection — как отпускът засяга DOO осигурителната база (НОИ-финансиран vs base-excluded vs нормален). Зададено за майчинство KT163/163-10/164/166 (Phase 1 #1.3) |

### `nssi.leave.reason` (нов)

17-те НЗОК болнични reason кода (`code` + `name`), seed-нати от
`data/nssi.leave.reason.csv`. Класифицират болничните за генериране
на НОИ удостоверения.

### `hr.leave.balance` (нов — SQL view)

Read-only `_auto=False` view: per `employee_id` × `leave_type_id`
разпределени / използвани / оставащи дни. Захранва balance widgets
без преизчисление при всяко четене.

### `hr.leave` (разширен)

`l10n_bg_leave_reason_id` + `l10n_bg_show_paid_days_fields` —
показват reason кода и employer-paid-day input-ите върху заявката.

### `hr.leave.allocation` (разширен — Phase 5.2)

`l10n_bg_compute_pro_rata_days(...)` + `_l10n_bg_count_pro_rata_months`
— pro-rata годишен отпуск при постъпване/напускане в средата на
годината (правило за закръгляне на половин месец).

## Заредени данни

- `data/hr_holidays_data.xml` — 61-те типа: 4 платен-годишен
  (КТ 155-157), 8 граждански/обществен дълг (КТ 157), 4 специални
  (КТ 158-161), 7 майчинство/бащинство (КТ 163-168), 4 учебни
  (КТ 169-171а), + 17 НЗОК болнични (кодове 01-17).
- `data/hr_holidays_doo_treatment.xml` — DOO-treatment флагове
  (Phase 1 #1.3 третиране на майчинство).
- `data/nssi.leave.reason.csv` — НЗОК reason кодове.

## Изгледи

- Разширения на leave type / заявка (код + reason + платени дни)
- `hr_leave_balance_views.xml` — balance pivot/list
- **`hr_leave_schedule_views.xml`** — Годишен график на отпуски
  (Phase 5.1): year-mode календар, оцветен по служител + pivot
  (служител × месец) + paid-annual search филтър; меню под Time Off →
  Reports.

## Връзка с ТРЗ

`l10n_bg_hr_payroll_holidays` (EE) надгражда този: авто-създава НОИ
болнични удостоверения при одобрение и добавя **чл. 37а НРВПО**
уведомлението (Phase 2.4) за отпуски над 30 работни дни. Зададеното
тук DOO третиране захранва намалението на DOO базата при майчинство в
`l10n_bg_hr_payroll`.

## Зависимости

| Odoo базови | Българска локализация |
|---|---|
| `hr_contract`, `hr_holidays` | `l10n_bg` |

## Конфигурация

1. Инсталация → 61 типа отпуски + НЗОК reason кодове се зареждат автоматично.
2. HR → Configuration → Time Off Types: преглед на кодове/DOO третиране.
3. Създайте allocations за годишните типове; ползвайте pro-rata
   помощника за постъпили в средата на годината.
4. Time Off → Reports → Annual Leave Schedule за планиращия изглед.

## Известни ограничения

- `hr.leave.balance` е read-only SQL view (без write-back).
- Pro-rata помощникът прилага стандартното правило за половин месец;
  нестандартни договорни схеми изискват ръчно разпределение.

## Свързани

- Преглед на репозиторията: [`../OVERVIEW.bg.md`](../OVERVIEW.bg.md)
- ТРЗ consumer: `l10n-bulgaria-ee/l10n_bg_hr_payroll_holidays`
- Roadmap: `claude.ai/memory/project_payroll_personnel_roadmap_2026_05_13.md`
- `data/hr_leave_types_documentation_bg.md` — per-type легална референция
