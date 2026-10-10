# Bulgaria — Commodity Codes (HS6 / CN8 / TARIC10)

One Combined Nomenclature code on the **product variant** and everything
derived from it. This module is the common base for SAF-T, Intrastat,
SVFR and customs duty rates — they read the code through the helper
methods, not through the raw `hs_code`.

## The three codes

```
HS6     (6 digits, Harmonized System)           481710      = CN8[:6]
CN8     (8 digits, Combined Nomenclature)       48171000    = code[:8]
TARIC10 (10 digits, integrated EU tariff)       4817100000  = the code, when 10 digits
```

* **Source of truth** is the field "Commodity Code (CN/TARIC)"
  (`l10n_bg_commodity_code`) on the variant: TARIC10 when known (import
  customs declaration), otherwise CN8. Digits only, 8 or 10 long. Spaces
  and dots ("4817 10 00") are stripped on write; anything else is an error.
* CN8, HS6 and TARIC10 are computed (stored). Nothing is ever padded with
  zeros: HS6 + "00" or CN8 + "00" is not guaranteed to exist.
* The core `hs_code` of the template (stock_delivery) carries the **CN8**
  — the code common to all variants, or empty when variants differ.
  Different CN8 codes between the variants of one template are allowed.
* "Commodity Code (CN/TARIC)" on the template: the variant's code for a
  single-variant product, the common code otherwise. Writing it on the
  template writes **all** variants.
* A manual write of `hs_code` (legacy path, imports) fills the source code
  of the variants that have none; an existing code is never overwritten.

* A **new variant** (attribute value added) inherits the common code when
  all active sibling variants share the same code; otherwise it gets none.
* **Combo products** (`type = combo`) are treated as goods: without a code
  they are exported to SAF-T with `0` and listed in the warning. Give them
  a code or leave them — a per-product decision.

## Yearly CN nomenclature

Inventory → Configuration → Combined Nomenclature (and Accounting →
Configuration → Combined Nomenclature). Write/import rights: Inventory /
Administrator and Accounting / Administrator.

The CN is re-adopted every year (regulation by 31 October, in force from
1 January). The nomenclature stores code + year + description +
supplementary unit. While the nomenclature of a year is empty, only the
format of the codes is checked.

### Import (CSV or XLSX)

Sources:

* **NRA** — Appendix 2 of the SAF-T documentation, sheet `NC8_TARIC`
  (about 9,900 codes for 2026);
* **NSI** — `CN_<year>.xlsx` (Combined Nomenclature).

The module ships no third-party data — download the file from the source
and import it every year after 31 October.

Expected format and parsing rules:

| What | How it is detected |
|---|---|
| Header row | within the first 30 rows — a row without an 8-digit code that has a code column (`CN8`, `CN code`, `Код по КН`, `Code` …) and at least one more recognised column |
| Code | 8 digits after removing spaces and dots ("0101 21 00" → 01012100). A 7-digit cell — number or text (Excel/CSV dropped the leading zero) — gets a leading zero |
| Description | column `Description` / `Описание` / `Наименование`; without a header row — the longest text of the row |
| Supplementary unit | column `Supplementary unit` / `Допълнителна мярка` / `SU`; `-` and `—` mean empty |
| Skipped | chapter and heading rows (2, 4, 6 digits), TARIC subdivisions (10 digits) and empty rows — their count is reported |

CSV: delimiter `,` `;` or tab (sniffed), UTF-8 or Windows-1251. XLSX needs
the optional Python library `openpyxl` (without it only CSV is accepted).
When no sheet is given, a sheet named like `NC8_TARIC` or `CN_<year>` is
preferred, otherwise the first sheet.

"Archive Codes Missing from the File" — for a complete nomenclature file:
the codes of the year that are not in the file are archived.

## Code status and filters

The status (OK, Missing, Invalid format, Not in nomenclature, Service) is
evaluated against the nomenclature of the current year. Product list
filters: **"Missing commodity code"** and **"Invalid commodity code"**.

## Helper methods (for other modules)

| `product.product` method | Returns |
|---|---|
| `_l10n_bg_cn8(date=None)` | a valid CN8 or `''`; with a date it must also exist in the CN of that year |
| `_l10n_bg_saft_commodity_code(date)` | `00000000` for a service; the CN8 when valid for the year; otherwise `0` |
| `_l10n_bg_commodity_issues(date)` | list of reasons why the code cannot be reported |

## Migration on install

For every variant without a code: the template's `taric_code` (from
l10n_bg_tariff_code) when it has exactly 10 digits; otherwise the digits
of the template's `hs_code` when they are 8 or 10. A code found in the
product name is **not** written automatically.

When the CN8 part of the legacy `taric_code` (10 digits) and `hs_code`
differ, **nothing is written**: a WARNING with the list goes to the log and
a review note is posted on the template.

## "Suggest CN from product name"

Some products carry the code at the start of their name
("48171000_Envelope …"). The action (from the product list or the menu)
shows the suggestions; only the checked lines are written. Products that
already have a different code are unchecked and highlighted for review.
Every write leaves a note in the product's chatter.

## Yearly CN change

After 31 October: import the new CN for the next year and fix the codes
before 1 January. The "Invalid commodity code" filter checks against the
current year; checking against the next year before 1 January currently
needs a `date` context (e.g. `{'date': '2027-01-01'}` on the action) — a
dedicated "products whose CN8 is missing in the new year" report is an
open item.

## License

LGPL-3. Author: Rosen Vladimirov.
