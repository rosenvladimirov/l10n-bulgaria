# Bulgarian Accounting Reports — Base (l10n_bg_reports_audit)

**Engine module** for Bulgarian accounting and tax reporting in Odoo 18.
Provides the SQL query layer, the tag-based extraction framework and the
data catalog needed by all downstream Bulgarian report packages
(VAT, GFO, GOD, audit drill-down).

| | |
|---|---|
| **License** | LGPL-3 |
| **Status** | Production / Stable |
| **Maintainers** | Rosen Vladimirov, Deyan Lyubenov |
| **Repo** | [rosenvladimirov/l10n-bulgaria](https://github.com/rosenvladimirov/l10n-bulgaria) |
| **Conventions** | Engine only — no XML views. All UI ships in `l10n_bg_reports_config`. |

---

## Highlights

### VAT / NRA reporting (existing)
- VAT Declaration (Чл. 125 ЗДДС)
- Sales / Purchases ledgers
- VIES declaration
- 14 SQL view models with NRA-compliant CSV export (`Declar.txt`, `Pokupki.txt`, `Prodagbi.txt`, `Vies.txt`)
- Account tag extensions (`l10n_bg_applicability`, `l10n_bg_code`, `l10n_bg_tax_partner_id`)
- VAT Ratio history (Чл. 73, ал. 2) + Intrastat thresholds

### Annual financial reports — tag-based extraction (since 18.0.13+)
- **NSI Annex 1 catalog** — 309 ready-made tags by Order RD-05-796/27.11.2025 (SG 109/16.12.2025):
  - 125 Balance Sheet (gfo_balance)
  - 49 Profit & Loss (gfo_pl)
  - 11 Changes in Equity (gfo_equity)
  - 42 Cash Flow direct method (gfo_cf)
  - 82 Annual Activity Report annexes I-V (god)
- **Two new tag fields:**
  - `l10n_bg_extract_basis` — `balance` (cumulative) vs `turnover` (period only)
  - `l10n_bg_position` — `asset` / `liability_equity` / `revenue` / `expense` / `inflow` / `outflow` / `increase` / `decrease`
- **Constraint** validates position vs applicability.

### Layered tag resolution per move line
At posting time `account.move.line.account_tag_ids` is materialized as:

1. **Base:** `account.tag_ids` (standard Odoo)
2. **Extend:** `product.l10n_bg_account_tag_ids` (statistical NSI product tags)
3. **Override:** on receivable/payable accounts only,
   `partner.l10n_bg_tax_tag_(receivable|payable)_ids` replaces the
   `gfo_balance`/`god` tags inherited from the account (gfo_pl/cf/equity
   are preserved).

Context flag `l10n_bg_skip_report_tag_apply` skips the hook (used by
the recompute wizard and large data imports).

### 5 SQL view models per applicability
Granularity = one row per (tag × account):

| Model | Applicability | Positions |
|---|---|---|
| `account.bg.gfo.balance.line` | `gfo_balance` | asset, liability_equity |
| `account.bg.gfo.pl.line` | `gfo_pl` | revenue, expense |
| `account.bg.gfo.cf.line` | `gfo_cf` | inflow, outflow |
| `account.bg.gfo.equity.line` | `gfo_equity` | increase, decrease |
| `account.bg.god.line` | `god` | all |

Pre-computed signed `value` via SQL `CASE WHEN position = ... THEN ...`.

### Extractor (AbstractModel `l10n.bg.audit.extractor`)

```python
env['l10n.bg.audit.extractor'].extract(
    'gfo_balance', '2025-01-01', '2025-12-31', company_id,
)
# → [{tag_id, tag_name, l10n_bg_position, l10n_bg_extract_basis, value}, ...]

env['l10n.bg.audit.extractor'].extract_by_tag(
    tag_id, date_from, date_to, company_id,
)  # → float

env['l10n.bg.audit.extractor'].drill_down(
    tag_id, date_from, date_to, company_id,
)  # → account.move.line recordset
```

### Wizards
- **Auto-map GOD/GFO Tags** — applies default `account.tag_ids` from a
  built-in NSI-code → account-prefix dictionary; supports both BG chart
  variants (XXX.YYY and XXXYYY 6-digit).
- **Recompute BG Tags on Move Lines** — batch (10k chunks) re-runs the
  layered resolution on existing posted moves; required after changes
  to product / partner / account tags.

---

## Installation

Drop the module under any addons path. Depends on:

- `base`, `account`
- `l10n_bg`, `l10n_bg_ledger`, `l10n_bg_config`

```bash
git clone -b 18.0 https://github.com/rosenvladimirov/l10n-bulgaria.git
# Add path to odoo.conf addons_path, then:
odoo -i l10n_bg_reports_audit -d <db>
```

---

## Usage

1. Install the module.
2. In **Accounting → Configuration → Bulgarian Configuration**:
   - **Auto-map GOD/GFO Tags** → Preview → Apply
3. Tag products (NSI activity tags) on `product.template.l10n_bg_account_tag_ids`.
4. Tag partners (institutional sector) on
   `res.partner.l10n_bg_tax_tag_receivable_ids` /
   `l10n_bg_tax_tag_payable_ids`.
5. Post journal entries — tags materialize on each move line.
6. After bulk tag changes run **Recompute BG Tags on Move Lines** to
   refresh existing posted moves.

UI access for the data lives in `l10n_bg_reports_config`
(Accounting → Reporting → Bulgaria audit reports):

- GFO Balance / P&L / Cash Flow / Changes in Equity (list, pivot, graph)
- GOD (NSI activity report)
- VAT Sale / Purchase / VIES

---

## Public reference

- ДВ бр. 109 / 16.12.2025 — Заповед РД-05-796 (Приложения 1-15)
  https://dv.parliament.bg/DVPics/2025/109_25/7254_2.pdf
- NSI Annex 1 (non-financial enterprises):
  https://www.nsi.bg/pages/godishen-otchet-za-deinostta-na-nefinansovite-predpriyatiya-sastavyashti-balans-prez-2025-godina-856
- ИСБС portal: https://isbs.nsi.bg

---

## Authors

Rosen Vladimirov ([@rosenvladimirov](https://github.com/rosenvladimirov))
Deyan Lyubenov

[Bulgarian README](README.bg.md)
