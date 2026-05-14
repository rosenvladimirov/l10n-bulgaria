# Bulgarian Accounting Reports — Configuration (l10n_bg_reports_config)

**UI layer** for the Bulgarian Reports engine.
Ships all forms, lists, pivots, graphs, menus and wizard views for the
NRA (VAT) and NSI (GFO/GOD) reporting catalogs delivered by
`l10n_bg_reports_audit`.

| | |
|---|---|
| **License** | LGPL-3 |
| **Status** | Production / Stable |
| **Maintainers** | Rosen Vladimirov, Deyan Lyubenov |
| **Repo** | [rosenvladimirov/l10n-bulgaria](https://github.com/rosenvladimirov/l10n-bulgaria) |
| **Convention** | UI-only — Python lives in `l10n_bg_reports_audit`. |

---

## Highlights

### Menus
Under **Accounting → Reporting → Management → Bulgaria audit reports**:

- **VAT reports** — Sales, Purchases, VIES
- **Partner / Product** trail balance pivots
- **GFO Balance Sheet** (`account.bg.gfo.balance.line`)
- **GFO Profit & Loss** (`account.bg.gfo.pl.line`)
- **GFO Cash Flow** (`account.bg.gfo.cf.line`)
- **GFO Changes in Equity** (`account.bg.gfo.equity.line`)
- **GOD — NSI Activity Report** (`account.bg.god.line`)

Each report opens with `list, pivot, graph` view modes.

Under **Accounting → Configuration → Bulgarian Configuration**:

- Intrastat Thresholds
- VAT Ratio History (Art. 73)
- **Auto-map GOD/GFO Tags** — bulk-apply default tags to accounts
- **Recompute BG Tags on Move Lines** — retroactively refresh aml tags

### Form / list extensions
- `account.account.tag` form — show `l10n_bg_applicability`,
  `l10n_bg_extract_basis`, `l10n_bg_position`
- `account.account` form — `tag_ids` (standard) and `account_tag_ids`
  many2many widget
- `account.journal` form — `account_tag_ids`
- `account.move.line` form — group "BG Report Tags" with
  `account_tag_ids` (readonly when posted)
- `account.move.line` standalone tree — optional column after `tax_tag_ids`
- `account.move` form → Journal Items tab — optional column
  "BG Report Tags" after `tax_ids`
- `account.move` form → BG documents group — `l10n_bg_type_vat`,
  `l10n_bg_tax_tag_id`, `l10n_bg_doc_type`, `l10n_bg_delivery_type`,
  `l10n_bg_narration`, `l10n_bg_customs_base_amount`
- `res.company` form — Intrastat thresholds + VAT ratio history
- `res.partner` form — `l10n_bg_tax_tag_receivable_ids` /
  `l10n_bg_tax_tag_payable_ids` (institutional sector tags)
- `product.template` form — `l10n_bg_account_tag_ids` (NSI activity tags)

---

## Installation

```bash
odoo -i l10n_bg_reports_config -d <db>
```

Depends on:
- `base`, `account`
- `l10n_bg_reports_audit`
- `l10n_bg_config`, `l10n_bg_ledger`

---

## Authors

Rosen Vladimirov ([@rosenvladimirov](https://github.com/rosenvladimirov))
Deyan Lyubenov

[Bulgarian README](README.bg.md)
