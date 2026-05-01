# CLAUDE.md — `l10n_bg_fiscal_printer_datecs_pm`

> Inструкции за Claude Code при работа в този модул.
> Този файл се чете от Claude Code преди всеки edit. Кратък, фокусиран, с препратки.

## 1. Контекст

Този модул е **direct Python driver** за Datecs PM Communication Protocol v2.11.4, използван от новото поколение Datecs fiscal devices (FP-700 MX и сродни). Покрива fiscal операции в Odoo 18 — както back-office (фактуриране, MRP), така и POS (retail).

**НЕ е extension на `l10n_bg_erp_net_fp`** — този модул работи изцяло без ErpNet.FP. Двата модула съществуват паралелно.

Източник на истината за протокола: `docs/PROTOCOL_REFERENCE.md` + `docs/command_map.csv` + `docs/status_bits.csv` + `docs/error_codes.csv`. Тези файлове са дестилат от Datecs PDF v2.11.4 / 17-Nov-2022. **Никога не редактирай тези файлове ad-hoc** — ако намериш разлика между PDF-а и тях, корекцията се прави на отделен commit с reference към страницата от PDF-а.

## 2. Архитектурни инварианти (НЕ нарушавай)

1. **`drivers/` папката е pure-Python** — не импортира `odoo.*`. Това позволява тестване без Odoo и евентуално packaging като самостоятелен PyPI модул в бъдеще.
2. **Транспортите са еквивалентни и взаимозаменяеми** — `transport_serial.py` и `transport_tcp.py` имплементират един и същ `Transport` ABC. Frame layer е общ. Ако някой код в `drivers/pm_v2_11_4.py` знае за конкретен транспорт — bug е.
3. **Frame layer е stateless** — не пази session state. Sequence number се подава отвън.
4. **Session/state живее в Odoo моделите**, не в драйвера. Драйверът е stateless RPC over wire.
5. **Никога не блокирай Odoo worker thread за повече от 60s** — fiscal операции имат retry/timeout логика, всичко с device interaction се прави в bounded time. За операции като Z-report, които може да отнемат повече, се използва `queue_job` или background cron.

## 3. Топология (поддръжка за всичките три)

Модулът поддържа три deployment topology едновременно — конфигурацията на `l10n.bg.fp.device` определя коя:

| Topology | Поле `connection_type` | Кога |
|---|---|---|
| Локален Odoo + serial device | `serial` | Single-shop on-prem |
| Cloud Odoo + TCP printer през VPN | `tcp` | Multi-shop, OpenVPN като Konex-Tiva |
| Cloud Odoo + локален Python IoT agent | `agent` | RS232/USB device на отдалечен shop machine |

`agent` транспортът е тънък JSON-RPC protocol към `l10n_bg_fp_iot_agent` (отделен Python пакет, който се инсталира на shop machine — НЕ е Odoo addon).

## 4. Frame protocol invariants (от PDF v2.11.4)

```
Request:  <PRE=01> <LEN:4> <SEQ:1> <CMD:4> <DATA:0..496> <PST=05> <BCC:4> <EOT=03>
Response: <PRE=01> <LEN:4> <SEQ:1> <CMD:4> <DATA:0..480> <SEP=04> <STAT:8> <PST=05> <BCC:4> <EOT=03>
```

- `<LEN>`, `<CMD>`, `<BCC>` са **4-byte ASCII-hex с +0x30 offset** на всеки nibble (range 0x30..0x3F)
- `<LEN>` = байтове от `<PRE>` (изкл.) до `<PST>` (вкл.) + **fixed offset 0x20**
- `<BCC>` = checksum на байтовете от `<PRE>` (изкл.) до `<PST>` (вкл.)
- `<SEQ>` е binary 0x20..0xFF; следващият msg използва SEQ+1
- `<STAT>` 8 байта, **bit 7 на всеки байт винаги е 1** (range 0x80..0xFF)
- Tab (`\t` = 0x09) разделя параметри в `<DATA>`
- БГ текст е CP-1251 (потвърди при първа имплементация — провери срещу пример frame от PDF p.10)

Non-wrapped control bytes:
- `NAK = 0x15` — checksum/format грешка → host retry със същия SEQ
- `SYN = 0x16` — keep-alive докато slave обработва (на всеки 60ms)

Timing:
- Slave reply: ≤ 60ms (или SYN)
- Host timeout: 500ms преди retry
- N retries → declare device offline (default N=3)

## 5. Status interpretation (8 bytes)

`status.py` трябва да декодира status bytes в structured `FiscalStatus` dataclass. Виж `docs/status_bits.csv` за пълна таблица.

**Критични flags за всеки command:**
- `0.0 syntax error` или `0.1 invalid command` → command не е изпълнена, не повтаряй
- `0.5 general error` = OR на всички `#` flags
- `2.3 fiscal receipt open` — context за повечето операции
- `4.5 fiscal memory error` = OR на всички `*` flags в bytes 4-5
- `5.3 device fiscalized` — без това повечето команди ще fail-ват

**Приоритет на error reporting**: винаги първо `ErrorCode` от `<DATA>` (negative integer от error_codes.csv), след това status bits. Не показвай status bits на потребителя ако вече има explicit ErrorCode — само log-вай.

## 6. Error codes

457 error кода в 28 категории — виж `docs/error_codes.csv`. Всички са **отрицателни integer-и**. ErrorCode = 0 означава OK.

User-facing error messages трябва да са преведени на български в `i18n/bg.po`. Категории:
- 100xxx — generic fiscal device errors → потребителят може да опита retry
- 102xxx — ECR config errors (TAX number empty, headers empty) → admin action
- 105xxx — EJ errors → service intervention
- 110xxx — NRA server / fiscalization errors → critical, спри операцията
- 11xxxx, 12xxxx — peripheral errors (display, scanner, pinpad) → degraded mode

## 7. Команден индекс — приоритет на имплементация

Виж `docs/command_map.csv` за всичките 73 команди. Phase the implementation:

**Phase 1 — minimum viable (back-office invoice печат):**
- 0x4A (74) Read status — health check, called преди всичко
- 0x30 (48) Open fiscal receipt
- 0x31 (49) Sale registration
- 0x33 (51) Subtotal
- 0x35 (53) Payment & total
- 0x38 (56) Close fiscal receipt
- 0x3C (60) Cancel fiscal receipt — error recovery

**Phase 2 — back-office complete:**
- 0x39 (57) Invoice data (за fiscal **invoice** receipt, не cash receipt)
- 0x6D (109) Print duplicate of last receipt
- 0x46 (70) Cash in / Cash out (служебно въведено / изведено)
- 0x45 (69) X/Z reports — задължителни в края на деня

**Phase 3 — POS specific:**
- 0x37 (55) Pinpad commands — 15 sub-options, голяма повърхност, прави го отделно
- 0x3A (58) Sale of programmed item (от PLU база)
- 0x6B (107) Item programming — sub-options 'P', 'I', 'A', 'D', 'R', 'F', 'L', 'N', 'X', 'x'

**Phase 4 — admin/maintenance:**
- 0x53 (83) VAT rate programming
- 0x62 (98) TAX number
- 0x7E (126) Fiscal memory structured info — за reporting
- 0xFF (255) Parameters write/read — само admin
- 0xFD (253) Service operations — изисква service password

## 8. POS workflow — happy path

```
Frontend (POS OWL)              Backend                          Device
     │                              │                                │
     ├── start_receipt() ──────────▶│                                │
     │                              ├── 0x4A (status check) ────────▶│
     │                              │◀────────────────── status ─────┤
     │                              ├── 0x30 (open receipt) ────────▶│
     │                              │◀──────────────── slip# 0 ──────┤
     │                              │                                │
     │  for each line:              │                                │
     ├── add_line(item) ───────────▶├── 0x31 (sale) ────────────────▶│
     │                              │◀────────────── status,total ───┤
     │                              │                                │
     ├── total() ──────────────────▶├── 0x33 (subtotal) ────────────▶│
     │                              │◀────────────── subtotal ───────┤
     ├── pay(method, amt) ─────────▶├── 0x35 (payment) ─────────────▶│
     │                              │◀────────────── change ─────────┤
     ├── close() ──────────────────▶├── 0x38 (close) ───────────────▶│
     │                              │◀────────────── slip closed ────┤
     │◀───────── slip#, fiscal_id ──┤                                │
```

Error recovery: при error след `0x30` open, винаги извикай `0x3C` cancel преди да се откажеш. Иначе device остава с отворена receipt и блокира следващите операции.

## 9. Тестване

`tests/` структура:
- `test_frame.py` — bit-level frame encode/decode, без device
- `test_codec.py` — CP-1251 round-trip за БГ текст
- `test_commands.py` — всяка команда срещу `MockDevice` (in-memory replay)
- `tests/fixtures/captured_*.bin` — реални frame captures от device, replay-ват се в integration tests

**Преди commit винаги:**
```bash
cd l10n_bg_fiscal_printer_datecs_pm
python -m pytest tests/ -v
ruff check .
ruff format --check .
```

Не commit-вай ако има skipped tests без TODO коментар.

## 10. NRA compliance (БГ specific)

Този модул трябва да удовлетворява:
- **Наредба Н-18** за касови апарати с НАП connectivity
- **Регистър на НАП** — fiscal device ID (cmd 0x7E sub-option 3)
- **EJ (КЛЕН)** integrity — не модифицирай cmd 0x7D handlers без consult с Боян
- **SAF-T export pipeline** — този модул feed-ва `l10n_bg_saf_t` с fiscal receipt data; не променяй receipt model schema без да syncнеш със SAF-T работата

Когато имплементираш fiscalization commands (0x48 cmd 72), всяка стъпка се audit-log-ва в `l10n.bg.fp.fiscalization.log` с timestamp и raw frames.

## 11. Какво ДА ПОПИТАШ преди да правиш

- Всякаква промяна в receipt schema → попитай преди commit
- Всякаква промяна в `drivers/frame.py` checksum логика → попитай (има captured fixtures които трябва да продължат да минават)
- Добавяне на нова команда extension от друга PM версия → попитай (поддържаме само v2.11.4 за момента, version negotiation е следваща Phase)
- Каквото и да е свързано с `0xFD` (Service operations) → попитай винаги, тези команди може да обезсилят fiscal certification

## 12. Какво НЕ е в scope на този модул

- Direct browser-side WebSerial/WebUSB driver (POS преминава винаги през backend, освен ако topology е `agent`)
- ErpNet.FP integration — това е `l10n_bg_erp_net_fp`, отделен модул
- Tremol/Eltrade/Daisy support — отделни sibling drivers ще се правят отделно
- Generic POS hardware (cash drawer, scanner, customer display извън fiscal device) — base Odoo IoT покрива тези

---

**Последна редакция:** 2026-05-01 — initial scaffold от protocol PDF v2.11.4 / 17-Nov-2022
