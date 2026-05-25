# l10n_bg_waste_base

**License:** AGPL-3.0
**Target Odoo:** 19.0
**Category:** Localization/Bulgaria

Foundation module of the Bulgarian waste management stack. Provides the
master data and reusable mixins used by every downstream waste module
(permit, picking, report). Implements the regulatory model defined by
**Наредба №2/2014** (waste classification) and the **Waste Management Act
(ЗУО)**.

## Provides

| Model | Purpose |
|---|---|
| `l10n.bg.waste.code` | Waste code catalog — Annex 1 of Наредба №2/2014, 6-digit hierarchy with hazardous flag and mirror-code pairs (Art. 10). |
| `l10n.bg.waste.activity` | R1–R13 recovery + D1–D15 disposal activities per Annexes 1 & 2 of the supplementary provisions of ЗУО. |
| `l10n.bg.waste.site` | Treatment site (площадка) — physical location linked to one or more `stock.warehouse` records. |
| `res.partner` | Extended with `is_waste_operator` flag + allowed R/D activities. |
| `res.company` | Extended with `waste_manager_id` (responsible user for over-quota alerts). |

## Security groups

| Group | Inherits | Use case |
|---|---|---|
| `group_waste_user` | `stock.group_stock_user` | Reads catalog, drives waste pickings, enters codes through wizard. |
| `group_waste_manager` | `group_waste_user` | Manages permits & quotas, receives over-quota notifications. |
| `group_waste_admin` | `group_waste_manager` + `base.group_system` | Edits master catalog, site ↔ warehouse links. |

## Seed data shipped

- **20 chapters** (2-digit) — full set from Annex 1.
- **Polygroup-relevant codes** (plastic recycling, R3): `02 01 04`, `07 02 13`,
  `12 01 05`, `15 01 02`, `16 01 19`, `17 02 03`, `19 12 04`, `20 01 39`
  plus their parent subchapters.
- **All R1–R13 + D1–D15** activities with English & Bulgarian translations.

> The full ~840-code catalog is **not yet shipped**; only Polygroup
> stream + chapters are seeded. To generate the full list:
>
> ```bash
> cd l10n_bg_waste_base/tools/
> python3 fetch_full_seed.py > ../data/waste_code_data_full.xml
> ```
>
> Then add `data/waste_code_data_full.xml` to `__manifest__.py` and
> `-u l10n_bg_waste_base`. **Preserve the existing `xml_id`s**
> (`waste_code_XX_YY_ZZ`) for upgrade compatibility — the script's
> `to_xml` uses the same naming convention.
>
> The MOEW PDF currently returns an HTML anti-bot landing for non-browser
> User-Agents; the script sends `Mozilla/5.0` to bypass. If MOEW changes
> the URL, fall back to the European Waste Catalogue (Commission Decision
> 2000/532/EC) — the codes are byte-identical with the BG transposition.

## Companion modules

- [`l10n_bg_waste_permit`](../l10n_bg_waste_permit/) — permits and quotas with online usage compute.
- [`l10n_bg_waste_picking`](../l10n_bg_waste_picking/) — stock.picking / move.line / lot integration.
- [`l10n_bg_waste_report`](../l10n_bg_waste_report/) — Annex 4 (monthly) and Annex 18 (annual) XLSX reports.

## Regulatory references

- [Наредба №2/2014 — класификация на отпадъците (МОСВ)](https://www.moew.government.bg/bg/otpaduci/klasifikaciya-na-otpaducite/)
- [Закон за управление на отпадъците (ЗУО)](https://lex.bg/laws/ldoc/2135836485)
- [Наредба №1/2014 — отчетност и образци](https://eea.government.bg/bg/nsmos/waste/naredba-1)
