# Българска счетоводна отчетност — База (l10n_bg_reports_audit)

**Технически модул** за българската счетоводна и данъчна отчетност в Odoo 18.
Предоставя SQL заявковия слой, tag-based extraction рамката и каталога с
данни, които ползват всички downstream български пакети за отчети
(ДДС, ГФО, ГОД, drill-down).

| | |
|---|---|
| **Лиценз** | LGPL-3 |
| **Статус** | Production / Stable |
| **Поддръжка** | Росен Владимиров, Деян Любенов |
| **Repo** | [rosenvladimirov/l10n-bulgaria](https://github.com/rosenvladimirov/l10n-bulgaria) |
| **Конвенция** | Само engine — без XML views. UI идва от `l10n_bg_reports_config`. |

---

## Основни функционалности

### ДДС / НАП отчети (съществуващи)
- Справка-декларация по ДДС (чл. 125 ЗДДС)
- Дневник на продажбите / покупките
- VIES декларация
- 14 SQL view модела с NRA-съвместим CSV експорт (`Declar.txt`, `Pokupki.txt`, `Prodagbi.txt`, `Vies.txt`)
- Разширения на account tags (`l10n_bg_applicability`, `l10n_bg_code`, `l10n_bg_tax_partner_id`)
- История на ДДС коефициента (чл. 73, ал. 2) + Intrastat прагове

### Годишни финансови отчети — tag-based extraction (от 18.0.13+)
- **Каталог по НСИ Приложение 1** — 309 готови tag-а по Заповед РД-05-796/27.11.2025 (ДВ бр. 109/16.12.2025):
  - 125 Баланс (gfo_balance)
  - 49 ОПР (gfo_pl)
  - 11 ОСК (gfo_equity)
  - 42 ОПП пряк метод (gfo_cf)
  - 82 ГОД доп. справки I-V (god)
- **Две нови полета на tag:**
  - `l10n_bg_extract_basis` — `balance` (кумулативно) vs `turnover` (само за периода)
  - `l10n_bg_position` — `asset` / `liability_equity` / `revenue` / `expense` / `inflow` / `outflow` / `increase` / `decrease`
- **Валидация** че позицията съответства на applicability категорията.

### Слойна резолюция на tag-овете на ниво счетоводен ред
При posting `account.move.line.account_tag_ids` се материализира като:

1. **База:** `account.tag_ids` (стандартното Odoo поле)
2. **Допълва:** `product.l10n_bg_account_tag_ids` (статистически НСИ tag-ове за продукта)
3. **Override:** само за вземания/задължения сметки,
   `partner.l10n_bg_tax_tag_(receivable|payable)_ids` заменя
   `gfo_balance`/`god` tag-овете наследени от сметката (gfo_pl/cf/equity
   се запазват).

Контекстен флаг `l10n_bg_skip_report_tag_apply` skip-ва hook-а (използва
се от recompute wizard-а и масови импорти).

### 5 SQL view модела per applicability
Гранулярност = един ред per (tag × сметка):

| Модел | Applicability | Позиции |
|---|---|---|
| `account.bg.gfo.balance.line` | `gfo_balance` | asset, liability_equity |
| `account.bg.gfo.pl.line` | `gfo_pl` | revenue, expense |
| `account.bg.gfo.cf.line` | `gfo_cf` | inflow, outflow |
| `account.bg.gfo.equity.line` | `gfo_equity` | increase, decrease |
| `account.bg.god.line` | `god` | всички |

Пресметната `value` (signed) през SQL `CASE WHEN position = ... THEN ...`.

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
)  # → recordset на account.move.line
```

### Wizard-и
- **Auto-map GOD/GFO Tags** — присвоява default `account.tag_ids` от
  вграден речник НСИ-код → префикс на сметкоплана; поддържа двата
  български chart варианта (XXX.YYY и XXXYYY 6-цифров).
- **Recompute BG Tags on Move Lines** — на пакети (10k наведнъж) re-run
  на слоената резолюция върху съществуващи posted moves; необходим
  след промени в product / partner / account tags.

---

## Инсталация

Постави модула в който и да е addons path. Зависимости:

- `base`, `account`
- `l10n_bg`, `l10n_bg_ledger`, `l10n_bg_config`

```bash
git clone -b 18.0 https://github.com/rosenvladimirov/l10n-bulgaria.git
# Добави пътя в odoo.conf addons_path, после:
odoo -i l10n_bg_reports_audit -d <db>
```

---

## Употреба

1. Инсталирай модула.
2. В **Счетоводство → Конфигурация → Bulgarian Configuration**:
   - **Auto-map GOD/GFO Tags** → Preview → Apply
3. Тагни продуктите (НСИ tag-ове за дейност) на `product.template.l10n_bg_account_tag_ids`.
4. Тагни партньорите (институционален сектор) на
   `res.partner.l10n_bg_tax_tag_receivable_ids` /
   `l10n_bg_tax_tag_payable_ids`.
5. Публикувай счетоводни статии — tag-овете се материализират на всеки ред.
6. След масови промени в tag-овете пусни **Recompute BG Tags on Move Lines**
   да обновиш съществуващите publish-нати статии.

UI достъп до данните живее в `l10n_bg_reports_config`
(Счетоводство → Отчети → Bulgaria audit reports):

- ГФО Баланс / ОПР / ОПП / ОСК (list, pivot, graph)
- ГОД (НСИ)
- ДДС Продажби / Покупки / VIES

---

## Публични източници

- ДВ бр. 109 / 16.12.2025 — Заповед РД-05-796 (Приложения 1-15)
  https://dv.parliament.bg/DVPics/2025/109_25/7254_2.pdf
- НСИ Приложение 1 (нефинансови предприятия):
  https://www.nsi.bg/pages/godishen-otchet-za-deinostta-na-nefinansovite-predpriyatiya-sastavyashti-balans-prez-2025-godina-856
- ИСБС портал: https://isbs.nsi.bg

---

## Автори

Росен Владимиров ([@rosenvladimirov](https://github.com/rosenvladimirov))
Деян Любенов

[English README](README.md)
