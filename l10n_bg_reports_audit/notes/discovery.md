# Discovery Results — Tag-Based Extraction (Pre-implementation Inventory)

Date: 2026-05-13
Branch: 18.0
Concept doc: `~/Свалени/CLAUDE_l10n_bg_reports_audit_tags.md`
Scope: Какво съществува преди да добавим `bg_extract_basis`, `bg_position`, intersect logic.

---

## A. `l10n_bg_config` — съществуващи разширения

### `account.account.tag` inherit
File: `l10n_bg_config/models/account_account_tag.py`

| Поле | Тип | line | Бележка |
|---|---|---|---|
| `description` | Text translate | :8 | Свободно описание на tag-а |

### `account.move` inherit
File: `l10n_bg_config/models/account_move.py`

| Поле | Тип | line |
|---|---|---|
| `l10n_bg_document_number` | Char (compute/inverse/search/store/trigram/tracking) | :11-20 |
| `l10n_bg_name` | Char (related='l10n_bg_document_number', store, readonly=False) | :23-28 |
| `l10n_bg_name_value` | Char | :29-32 |
| `l10n_bg_date` | Date | :33 |
| `l10n_bg_deal_date` | Date (compute/store) | :34 |

### `account.move.line` inherit
File: `l10n_bg_config/models/account_move_line.py` — no new fields, mixin only.

---

## B. `l10n_bg_reports_audit` — текущи разширения (важен за избягване на double-define)

### `account.account.tag` inherit
File: `models/account_account_tag.py`

| Поле | Тип | line | Стойности / бележка |
|---|---|---|---|
| `l10n_bg_applicability` | Selection (dynamic) | :11-13 | Източник: `_get_l10n_bg_applicability()` → `get_l10n_bg_applicability()` в `l10n_bg_file_helper.py:565-571`. Текущи: declaration, purchase, sale, vies |
| `l10n_bg_code` | Char (computed) | :14-16 | digits-only от name |
| `l10n_bg_tax_partner_id` | Many2one → res.partner | :17-21 | Partner за tax line при apply |
| `applicability` | Selection (selection_add) | :22-31 | Добавени: `l10n_bg_partner`, `l10n_bg_product`. Standard Odoo полета `accounts`/`taxes` остават; ondelete=set default |

### `account.move` inherit
File: `models/account_move.py`

| Поле | Тип | line | Бележка |
|---|---|---|---|
| `l10n_bg_customs_base_amount` | Float | :15-24 | Customs override |
| `l10n_bg_audit_use_tax` | Boolean (related, ro) | :25-28 | От res.company |
| `l10n_bg_type_vat` | Selection (12 стойности от `get_type_vat()`) | :30-36 | standard / 117_protocol_* / 119_report / in_customs / out_customs |
| `l10n_bg_narration` | Char translate | :38-42 | Аудит narration |
| `l10n_bg_exemption_reason` | Selection | :45-48 | 01-08 + 51-54 (delivery types) |
| `l10n_bg_doc_type` | Selection (related, store, rw) | :51-56 | |
| `l10n_bg_delivery_type` | Selection (related, store, rw) | :57-62 | |
| `l10n_bg_tax_tag_id` | Many2one → account.account.tag | :63-70 | Доп. BG tag за tax lines |

**Override-нати методи:**
- `write()` :77-94 — при промяна на `l10n_bg_tax_tag_id` извиква `_l10n_bg_remove_tax_tag()` + `_l10n_bg_apply_tax_tag()` на `line_ids` след super(). **Това е recommend pattern за нашия intersect hook също — write() на move triggers re-materialization.**

### `account.move.line` inherit
File: `models/account_move_line.py`

- Helper methods: `_l10n_bg_apply_tax_tag()`, `_l10n_bg_remove_tax_tag()`, `_l10n_bg_reset_tax_partner()` :12-109
- Override `create()` :111-116 — calls `_l10n_bg_apply_tax_tag()` после super()
- Override `write()` :118-124 — проверява context flag `l10n_bg_skip_tax_tag_apply` преди apply

**Контекст флагове в употреба:**
- `l10n_bg_skip_tax_tag_apply` :86, :97, :120 — избягва преприложение при ръчни tag манипулации
- `l10n_bg_skip_tax_closing_check` :87 — other validation skip
- `check_move_validity=False` :88 — стандартен Odoo flag

### `account.journal` inherit
File: `models/account_journal.py` — само метод `_l10n_bg_document_type_selection_values()`, **никакви нови полета**. Свободно за нашите.

### `account.account` inherit
**НЯМА** в `l10n_bg_reports_audit`. Свободно за наш inherit.

---

## C. `l10n_bg_reports_config` — UI/wizards

Не съдържа `account.account.tag` нови полета в models/, само views + wizard за bulk edit. Изграждаме нашия UI поверх него.

---

## D. `l10n_bg_ledger` — не съдържа inherit-и на нашите 5 модела (само ledger-specific).

---

## E. Категоризационни Selection полета вече в кода

| Поле | Модел | Източник | Стойности |
|---|---|---|---|
| `l10n_bg_applicability` | account.account.tag | `get_l10n_bg_applicability()` :565-571 | declaration, purchase, sale, vies |
| `l10n_bg_type_vat` | account.move | `get_type_vat()` :623-638 | 12 стойности |
| `l10n_bg_exemption_reason` | account.move | `get_delivery_type()` :641-670 | 01-08 + 51-54 |

**Извод:** Полето за категоризация на tag-ове в нашия модул е `l10n_bg_applicability`. Тъй като е dynamic Selection (function-based), **разширяването става чрез добавяне на стойности в `get_l10n_bg_applicability()` в `l10n_bg_file_helper.py`**, НЕ чрез `selection_add` на полето.

---

## F. Конфликти с предложените имена (от концепцията)

| Предложено име | Status | Бележка |
|---|---|---|
| `bg_extract_basis` | ✅ свободно | не съществува |
| `bg_position` | ✅ свободно | не съществува |
| `bg_report_description` | ✅ свободно | `description` вече има на тag (config :8) — наш ще е специфичен текст за отчета |
| `account_tag_ids` на account.account | ✅ свободно | няма inherit |
| `account_tag_ids` на account.journal | ✅ свободно | няма поле |
| `account_tag_ids` на account.move.line | ✅ свободно | няма поле |
| `bg_storno` | ✅ свободно | не съществува |

**Внимание:** На `product.template/product.product` вече има `l10n_bg_account_tag_ids` (audit `products.py:10-18`) с relation `l10n_bg_product_template_account_tag_rel`. Това е **различен** field name (с `l10n_bg_` prefix) и **различен** relation — no collision.

---

## G. Relation table names в употреба

| Relation | Между | File:line |
|---|---|---|
| `l10n_bg_product_template_account_tag_rel` | product.template ↔ account.account.tag | `products.py:13` |
| `l10n_bg_partner_receivable_tag_rel` | res.partner ↔ account.account.tag | `res_partner.py:12` |
| `l10n_bg_partner_payable_tag_rel` | res.partner ↔ account.account.tag | `res_partner.py:22` |

**Препоръчвани нови (избягват колизия):**
- `l10n_bg_account_account_tag_rel` — за account.account ↔ tag
- `l10n_bg_account_journal_tag_rel` — за account.journal ↔ tag
- `l10n_bg_account_move_line_tag_rel` — за aml ↔ tag

---

## H. `account.move._post()` hook strategy

Odoo 18 source не е на локалната машина. Базирано на конвенциите в текущия audit код, recommend strategy:

**Опция 1 (preferred):** Override `account.move._post(soft=True)` в нашия `account_move.py`. След super() итерираме `line_ids` и пишем intersect на `account_tag_ids`. Context flag `l10n_bg_skip_report_tag_apply` за batch operations.

**Опция 2:** Hook в `account.move.line.create()` и `write()` (както съществуващия `_l10n_bg_apply_tax_tag` pattern). Недостатъкът: tag-овете се пълнят при create, преди да знаем move state — но за aml на posted moves това е същият момент.

**Решение:** Опция 1. `_post()` е semantically correct point: tag-овете трябва да са stable след posting и да не се пипат при draft edits. Това и съвпада с описанието в концепцията:
> aml.account_tag_ids = aml.account_id.account_tag_ids ∩ aml.journal_id.account_tag_ids
> Immutable след posting

---

## I. Tests

Текущ модул няма `tests/` директория. Създаваме нова, ползваме `odoo.tests.common.TransactionCase` + `tagged('post_install', '-at_install')`.

Препоръчителна структура:
```
tests/
├── __init__.py
├── common.py                    # base setup: company, accounts, journals, tags
├── test_intersect_materialization.py
├── test_position_formulas.py
├── test_storno_flip.py
├── test_extract_balance.py
├── test_extract_turnover.py
├── test_account_702_dual_tags.py    # критичен сценарий
└── test_wizard_recompute.py
```

---

## J. Решения, които правим преди да започнем имплементацията

1. **Категоризация → разширяване на `l10n_bg_applicability`** с `gfo_balance`, `gfo_pl`, `gfo_cf`, `gfo_equity`, `god` в `get_l10n_bg_applicability()`.
2. **Нови полета на tag**: `bg_extract_basis`, `bg_position`, `bg_report_description`, `bg_account_ids`, `bg_journal_ids`.
3. **Нови M2M**: `account_tag_ids` на account.account / account.journal / account.move.line с relation таблиците по-горе.
4. **bg_storno** като Boolean на journal.
5. **`_post()` override** в `account.move` за intersect materialization (context flag `l10n_bg_skip_report_tag_apply`).
6. **AbstractModel** `l10n.bg.audit.extractor` за extract_by_tag / drill_down.
7. **Wizard** `l10n.bg.recompute.report.tags.wizard` за retroactive popуlate.
8. **Constraint** `_check_position_matches_applicability` на tag.
9. **Manifest bump** 18.0.12.1.0 → 18.0.13.0.0 (минорно breaking — нови полета на account.account/journal/aml, които могат да повлияят на отчети).
10. **No migration script** засега — нови полета са optional, intersect се popуlate-ва при следващо posting или wizard.
