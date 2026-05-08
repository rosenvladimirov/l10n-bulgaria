# External POS режим (БГ)

`l10n_bg_external_pos_mode` — toggle на `pos.config` който обръща ролята между Odoo POS и фискалния апарат.

## Какво прави

| Без external mode (default) | С external mode |
|---|---|
| Касиер тъпка cart в Odoo POS UI | Касиер бие PLU/баркод **директно на апарата** |
| Apparat-ът = тих receipt printer | Apparat-ът = primary POS |
| Промените се синхронизират в реално време | Push-ва се на open + import на close |
| Resilient до browser crash | Resilient до full network outage |

## Защо съществува (БГ контекст)

1. **Наредба Н-18** изисква фискалният контрол да е *на устройството*, не през software layer
2. **Скорост** — касиерка чете 200 баркода/час; tablet UI е bottleneck
3. **Малки магазини** — един бутон "отвори/затвори смяна" е достатъчно
4. **Resilience** — net пада, апаратът продава сам, Odoo прибира данните после

## Setup за първа употреба

### 1. Активирай external mode на POS config-а

```
Settings → Point of Sale → POS Config → Cash register as POS (external) ✓
                                      → Auto Z on POS close ✓ (recommended)
```

### 2. Закачи фискален апарат

```
POS Config → Fiscal printer ← (primary device, M2o)
          → Additional fiscal printers ← (multi-device shops)
```

⚠️ Ще получиш UserError ако активираш external mode без поне 1 device.

### 3. Изгради PLU базата

`Point of Sale → Fiscal Printers → Fiscal PLU` — слотовете в апарата.

**Опции:**

A. **Bulk allocate** — на product list избери продукти → действие "Add to fiscal PLU base":
   - Wizard auto-allocate-ва next free PLU number за всеки
   - Snapshot-ва name + price от текущия pricelist
   - Skip-ва вече свързани продукти

B. **Manual** — създай PLU slot ръчно, прикачи 1+ продукта (M2M)
   - М2М за **synonymous items** (Хляб бял от 3 доставчика → 1 PLU)
   - М2М за **bundles** (3-за-5лв → {хляб + сирене + кафе})
   - М2М за **variant collapsing** (3 вкуса сладолед same price)

### 4. Настрой VAT mapping

`Accounting → Configuration → Tax Groups`:
- Всяка група на която има БГ артикули → **Tax group** = А/Б/В/Г

Пример БГ:
- А (0% ДДС) — лекарства, хляб
- Б (20% ДДС) — стандарт
- В (20% ДДС) — gas/petrol (отделна група за Н-18)
- Г (9% ДДС) — туризъм, хотели

### 5. Настрой payment kind

`POS → Payment Methods`:
- За всеки method → **External-mode payment kind** = cash / card / voucher / other

Без mapping → всички imported receipts отиват на default cash method.

### 6. Настрой касиерите (optional)

`Settings → Users` → за всеки касиер:
- **Cashier operator code** — 1-99 (apparat slot)
- **Cashier operator password** — 8-цифрен (apparat auth)

Без code → apparat-ът ползва own config.yaml оператори.

## Дневна употреба

### Отваряне на смяна

1. Касиер натиска **"Open POS"** в Odoo
2. Background → push на VAT groups + operators + PLU table + logo + header към устройството
3. X-report за sanity (стартова сума)
4. POS UI badge показва **"Device ready"**
5. Apparat-ът готов за продажби

При **partial** или **error** → **"Retry external-mode push"** button се появява.

### Продажби

Касиер бие на апарата:
- `142 PLU` → апаратът избива #142 със snapshot цена
- Или сканира баркод → апаратът преобразува към PLU
- Apparat-ът пуска бона; Odoo НЕ знае нищо

### Затваряне на смяна

1. Касиер натиска **"Close POS"** в Odoo
2. Background → pull journal от apparat → import receipts като pos.order
3. Auto-Z (ако enabled) → apparat принтира Z report → close fiscal.session
4. Discrepancy check: `imported_total - z_total`
5. Standard Odoo close-control wizard потвърждава cash counts

При offline apparat → **"Force-close (no device)"** маркира `closed_partial` за ръчен reconcile.

## Mid-shift операции

### X-report

`pos.session form → Action → "X-report (mid-shift)"`:
- Избор на device (multi-device)
- Inline preview на response (totals, register state)
- Не нулира нищо — само snapshot

### Промяна на цени

⚠️ **НИКОГА не push-вай цени mid-shift** — апаратът смесва стари receipts с new price = chaos в audit trail.

При промяна на product/pricelist:
- Auto-trigger → засегнатите PLUs стават `stale` (push_state)
- Push НЕ се случва веднага
- На следващ open → re-validate + push

При close → warning ако има stale PLUs.

## Resilience features

| Сценарий | Поведение |
|---|---|
| **Net pада** | Apparat продава сам; pull on close прибира всичко |
| **Apparat off на open** | Push fails partial; "Retry" button когато се reconnect |
| **Касиер забравил close** | Cron 23:55 daily → auto-close с Z (Н-18 ≤24h limit) |
| **Z-report fails** | Retry × 3; permanent fail → fiscal.session `closed_partial` + mail.activity до manager |
| **PLU overflow** | Pre-push UserError → "Top-N best-sellers" wizard archives losers |
| **Receipts lost mid-pull** | Discrepancy ≠ 0 → red в fiscal.session list + form |

## Multi-device магазини

За 2+ каси в същия магазин:
- Primary device на pos.config + extras в M2M
- Push iterates всички — same PLU table mirror-нат към всичките
- Всеки device → own fiscal.session + own Z-cycle
- Receipt dedupe по `(device_id, receipt_number)` (различен FP на различни апарати може да издадат receipt 142 в същия ден)

## Troubleshooting

### "External-POS mode requires a fiscal printer device assigned first"

Активирал си toggle-а без да си закачил device. Закачи в Fiscal printer (primary) или Additional fiscal printers.

### Push partial — "vat_groups: Skipped/failed"

Tax groups нямат БГ letter (`l10n_bg_fiscal_tax_group`). Конфигурирай в Accounting → Tax Groups.

### Discrepancy ≠ 0 при close

Възможни причини:
1. **Unknown PLU в receipt** — apparat-ът имал слот, който не е в Odoo PLU базата (ръчно добавен на устройството?). Виж log за warnings.
2. **Receipt parsing fail** — apparat-ът върна непознат payment kind. Конфигурирай `l10n_bg_external_kind` на всички payment methods.
3. **Mid-pull network issue** — част от receipts не са pull-нати. Manual pull чрез X-report wizard за compare.

### "Z-report failed after retries"

Apparat-ът върна transient грешка 3 пъти. Common причини:
- Хартията свърши — смени, manual Z от устройството
- Apparat-ът е в auth lock — отвори смяна на касиера на устройството

След manual fix → отваряш fiscal.session record → "Action → Manual Z" (TODO на Phase 6).

### PLU "conflict" state

Различни products в M2M имат различни pricelist цени. Examples:
- Хляб бял A 2.50 + Хляб бял B 2.70 → split в 2 PLUs или sync price
- Promo bundle с product changing price → wait until promo ends

Не push-ва нищо за този PLU докато не resolve-нeш ръчно.

## Capacity planning

| Device | PLU capacity | Recommended активни |
|---|---|---|
| Datecs DP-150 | 1000-3000 | < 1500 |
| Datecs FP-700X | 3000 | < 2500 |
| Datecs PM | 10000 | < 8000 |
| Tremol M20 | 5000-10000 | < 4500 |
| Daisy серия | 1500-3000 | < 1500 |

При over-capacity → **Top-N best-sellers wizard** ranks by 90-day sales velocity, archives bottom.

## Telemetry

Grafana dashboard JSON в `static/grafana/external_pos_mode_dashboard.json`:
- Receipts/h trend
- Open fiscal sessions count
- Force-closed count (last 7d)
- Z-report duration histogram
- Discrepancy distribution
- Push success rate
- Top PLUs by velocity

Импортирай в Grafana с Postgres datasource към Odoo db.

## Свързани модели

| Model | Role |
|---|---|
| `pos.config` | Toggle + primary/extra devices |
| `pos.session` | Browser shift container; trigger push on open, pull on close |
| `fiscal.session` | Z-cycle marker (1 per device per pos.session) |
| `l10n.bg.fiscal.plu` | PLU registry (per-company, M2M to product.product) |
| `fiscal.printer.device` | Device record + push helpers (`_l10n_bg_push_*`) |

## Roadmap (post v18.0.11.x)

- Phase 6: Manual Z trigger от fiscal.session admin
- Phase 6: Per-PLU push status за debug на single-PLU sync
- Phase 7: POS UI button за refresh price snapshot за demo при manual override
- Phase 7: Reconcile wizard за `closed_partial` sessions
