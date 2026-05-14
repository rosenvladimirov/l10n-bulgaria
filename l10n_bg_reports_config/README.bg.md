# Българска счетоводна отчетност — Конфигурация (l10n_bg_reports_config)

**UI слой** за engine-а на българските отчети.
Доставя всички форми, списъци, pivot/graph view-та, менюта и wizard
view-та за НАП (ДДС) и НСИ (ГФО/ГОД) каталозите от
`l10n_bg_reports_audit`.

| | |
|---|---|
| **Лиценз** | LGPL-3 |
| **Статус** | Production / Stable |
| **Поддръжка** | Росен Владимиров, Деян Любенов |
| **Repo** | [rosenvladimirov/l10n-bulgaria](https://github.com/rosenvladimirov/l10n-bulgaria) |
| **Конвенция** | Само UI — Python кодът е в `l10n_bg_reports_audit`. |

---

## Основни функционалности

### Менюта
Под **Счетоводство → Отчети → Управление → Bulgaria audit reports**:

- **ДДС отчети** — Продажби, Покупки, VIES
- **Партньорски / Продуктови** pivot-и
- **ГФО Баланс** (`account.bg.gfo.balance.line`)
- **ГФО ОПР** (`account.bg.gfo.pl.line`)
- **ГФО ОПП** (`account.bg.gfo.cf.line`)
- **ГФО ОСК** (`account.bg.gfo.equity.line`)
- **ГОД — НСИ** (`account.bg.god.line`)

Всеки отчет се отваря в `list, pivot, graph` режим.

Под **Счетоводство → Конфигурация → Bulgarian Configuration**:

- Intrastat прагове
- ДДС коефициент — история (чл. 73)
- **Auto-map GOD/GFO Tags** — масово прилагане на default tag-ове върху сметки
- **Recompute BG Tags on Move Lines** — ретроактивно обновяване на aml tag-овете

### Разширения на форми / списъци
- `account.account.tag` форма — показва `l10n_bg_applicability`,
  `l10n_bg_extract_basis`, `l10n_bg_position`
- `account.account` форма — `tag_ids` (стандартно) + `account_tag_ids`
  many2many widget
- `account.journal` форма — `account_tag_ids`
- `account.move.line` форма — група "BG Report Tags" с
  `account_tag_ids` (read-only при posted)
- `account.move.line` standalone tree — optional колона след `tax_tag_ids`
- `account.move` форма → Счетоводна операция таб — optional колона
  "BG Report Tags" след `tax_ids`
- `account.move` форма → БГ група документи — `l10n_bg_type_vat`,
  `l10n_bg_tax_tag_id`, `l10n_bg_doc_type`, `l10n_bg_delivery_type`,
  `l10n_bg_narration`, `l10n_bg_customs_base_amount`
- `res.company` форма — Intrastat прагове + ДДС коефициент история
- `res.partner` форма — `l10n_bg_tax_tag_receivable_ids` /
  `l10n_bg_tax_tag_payable_ids` (институционални секторни tag-ове)
- `product.template` форма — `l10n_bg_account_tag_ids` (НСИ tag-ове за дейност)

---

## Инсталация

```bash
odoo -i l10n_bg_reports_config -d <db>
```

Зависимости:
- `base`, `account`
- `l10n_bg_reports_audit`
- `l10n_bg_config`, `l10n_bg_ledger`

---

## Автори

Росен Владимиров ([@rosenvladimirov](https://github.com/rosenvladimirov))
Деян Любенов

[English README](README.md)
