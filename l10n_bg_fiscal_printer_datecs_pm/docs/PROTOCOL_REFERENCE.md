# Datecs PM Communication Protocol v2.11.4 — дестилирана reference

> Извадено от `PM_XXXXXX-BUL_CommunicationProtocol_v2.11.4.pdf`
> (Datecs, 17-Nov-2022, 136 страници, LibreOffice 7.2 generated).
> Авторски права: © Datecs Ltd. Протоколът може да се използва свободно
> за писане на драйвери (по чл. 2 от PDF-а).

## 1. Транспорт

### Serial
- Baud: 1200 / 2400 / 4800 / 9600 / 19200 / 38400 / 57600 / 115200
- Frame format: 8N1
- Flow control: none

### TCP
- Port и mode се конфигурират на устройството (виж user manual)
- Frame envelope identical with serial
- Speed не се конфигурира

## 2. Frame envelope

### Request (host → device)

| Field | Bytes | Value | Описание |
|---|---|---|---|
| `<PRE>` | 1 | `0x01` | Preamble |
| `<LEN>` | 4 | `0x30..0x3F` × 4 | ASCII-hex дължина с +0x20 offset; брой байтове от <PRE> (изкл.) до <PST> (вкл.) + 0x20 |
| `<SEQ>` | 1 | `0x20..0xFF` | Sequence number; device echo-ва същия |
| `<CMD>` | 4 | `0x30..0x3F` × 4 | ASCII-hex command code |
| `<DATA>` | 0..496 | `0x20..0xFF` | Параметри, разделени с `\t` (0x09) |
| `<PST>` | 1 | `0x05` | Postamble |
| `<BCC>` | 4 | `0x30..0x3F` × 4 | ASCII-hex checksum (sum от <PRE> изкл. до <PST> вкл.) |
| `<EOT>` | 1 | `0x03` | Terminator |

### Response (device → host)

Идентично с request-а, но с допълнителна `<SEP>` + `<STAT>` секция между `<DATA>` и `<PST>`:

| Field | Bytes | Value | Описание |
|---|---|---|---|
| `<SEP>` | 1 | `0x04` | Separator преди status |
| `<STAT>` | 8 | `0x80..0xFF` × 8 | Status байтове (bit 7 винаги = 1) |

`<DATA>` в response: 0..480 байта.

### ASCII-hex encoding

Всеки nibble (4 bits) става един byte чрез добавяне на `0x30`:
- nibble `0x0` → `'0'` = `0x30`
- nibble `0xF` → `'?'` = `0x3F`

Примери:
- LEN = 0x12 (decimal 18) → encode "0012" → bytes `0x30 0x30 0x31 0x32`
- LEN = 0xFF (decimal 255) → encode "00FF" → bytes `0x30 0x30 0x3F 0x3F`

### Checksum алгоритъм (BCC)

```
sum = 0
for byte in frame[after_PRE:through_PST_inclusive]:
    sum += byte
sum &= 0xFFFF                      # 16-bit
bcc = ascii_hex_4byte(sum)         # +0x30 на всеки nibble
```

### Length field

```
len = (count_of_bytes_from_after_PRE_to_PST_inclusive) + 0x20
```

Този `+0x20` offset е документиран explicitly в PDF p.2.

## 3. Non-wrapped control bytes

Slave може да върне един byte вместо frame:

| Byte | Hex | Значение |
|---|---|---|
| `NAK` | `0x15` | Slave намери checksum/format грешка → host да повтори със същия SEQ |
| `SYN` | `0x16` | Slave обработва, още не е готов → host да чака още 60ms |

## 4. Timing

- Slave first byte response: **≤ 60ms** (или wrapped frame, или single control byte)
- SYN repeat interval: **60ms** (докато slave обработва)
- Host receive timeout: **500ms** преди retry
- След N retries (recommend N=3): host обявява device offline

## 5. Status bytes (8 байта)

Bit 7 на всеки byte винаги е 1 (за да диференцира от control bytes).

**Mark legend:**
- `#` = error flag, OR-ва се в bit 0.5 (general error)
- `*` = error flag, OR-ва се в bit 4.5 (FM error aggregate)

### Byte 0 — General

| Bit | Mark | Описание |
|---|---|---|
| 7 | | Always 1 |
| 6 | `#` | Cover is open |
| 5 | | General error (OR на всички `#` flags) |
| 4 | | Failure in printing mechanism |
| 3 | | Always 0 |
| 2 | | RTC not synchronized |
| 1 | `#` | Command code is invalid |
| 0 | `#` | Syntax error |

### Byte 1 — General

| Bit | Mark | Описание |
|---|---|---|
| 7 | | Always 1 |
| 6-2 | | Always 0 |
| 1 | `#` | Command not permitted |
| 0 | `#` | Overflow during command execution |

### Byte 2 — Receipt state

| Bit | Mark | Описание |
|---|---|---|
| 7 | | Always 1 |
| 6 | | Always 0 |
| 5 | | Non-fiscal receipt is open |
| 4 | | EJ nearly full |
| 3 | | Fiscal receipt is open |
| 2 | | EJ is full |
| 1 | | Near paper end |
| 0 | `#` | End of paper |

### Byte 3 — Reserved (всички always 0/1)

### Byte 4 — Fiscal Memory

| Bit | Mark | Описание |
|---|---|---|
| 7 | | Always 1 |
| 6 | | Fiscal memory not found / damaged |
| 5 | | OR на всички `*` flags (Bytes 4-5) |
| 4 | `*` | Fiscal memory full |
| 3 | | <60 reports remaining in FM |
| 2 | | Serial+FM number set |
| 1 | | TAX number set |
| 0 | `*` | Error accessing FM data |

### Byte 5 — General

| Bit | Mark | Описание |
|---|---|---|
| 7 | | Always 1 |
| 6, 5 | | Always 0 |
| 4 | | VAT set at least once |
| 3 | | Device is fiscalized |
| 2 | | Always 0 |
| 1 | | FM is formatted |
| 0 | | Always 0 |

### Bytes 6, 7 — Reserved (всички always 0/1)

Пълна tabular reference: `command_map.csv` придружаващ файл.

## 6. Error codes

457 кода в 28 категории, всички negative integers. Виж `error_codes.csv`.

Категории:
- `100000-100009` Generic fiscal device errors
- `100100-100116` Fiscal memory
- `100400-100414` Printer mechanism (LTP)
- `100500-100511` System (RAM, flash, RTC, TPM)
- `101000-101017` Common logical (timeout, bad input, format)
- `102000-102020` ECR config (TAX#, headers, operator pwd)
- `103000-103008` PLU database
- `104000-104013` Service operations
- `105000-105019` EJ (КЛЕН)
- `106000-106004` Clients database
- `110100-110112` External fiscal device errors
- `110200+` NAP server errors
- `170000+` USB pendrive

При response с грешка: ErrorCode идва **в DATA payload** като отрицателен integer, плюс status bits се установяват съответно.

## 7. Параметри в DATA — синтаксис

- Параметри в DATA се разделят с **TAB (`\t` = 0x09)**
- Mandatory параметър — задължителен; ако липсва, syntax error
- Optional параметър — може да е празен, но `\t` separator пак трябва да е там
- DateTime формат: `DD-MM-YY hh:mm:ss DST` (DST = "DST" текст ако е активно лятно часово време, иначе omitted)

Example DATA payload:
```
1\t1\t24\tI\t
↓
hex: 31 09 31 09 32 34 09 49 09
```

## 8. Командни групи (workflow-aligned)

### A. Fiscal receipt lifecycle

| Cmd | Hex | Operation | Phase |
|---|---|---|---|
| 48 | 0x30 | Open fiscal receipt | 1 |
| 49 | 0x31 | Sale registration | 1 |
| 51 | 0x33 | Subtotal | 1 |
| 53 | 0x35 | Payment & total | 1 |
| 56 | 0x38 | Close fiscal receipt | 1 |
| 60 | 0x3C | Cancel fiscal receipt | 1 |
| 57 | 0x39 | Invoice data | 2 |
| 58 | 0x3A | Sale of programmed item | 3 |
| 109 | 0x6D | Print duplicate | 2 |
| 76 | 0x4C | Status of fiscal transaction | 1 |

### B. Non-fiscal receipt

| Cmd | Hex | Operation |
|---|---|---|
| 38 | 0x26 | Open non-fiscal receipt |
| 39 | 0x27 | Close non-fiscal receipt |
| 42 | 0x2A | Print free non-fiscal text |
| 54 | 0x36 | Print free fiscal text (внимание: вътре в fiscal receipt) |
| 122 | 0x7A | Free vertical fiscal text |

### C. Storno (refund)

| Cmd | Hex | Operation |
|---|---|---|
| 43 | 0x2B | Open storno document |

Параметрите за storno включват: original receipt number, original date, FM number, reason (типове 0-3 според Наредба Н-18).

### D. Reports

| Cmd | Hex | Operation |
|---|---|---|
| 69 | 0x45 | X/Z/D/G/P reports |
| 110 | 0x6E | Additional daily info (по 12 sub-options) |
| 105 | 0x69 | Operator report |
| 111 | 0x65 | PLU report |

### E. Status & info

| Cmd | Hex | Operation |
|---|---|---|
| 74 | 0x4A | Read status (8 bytes) |
| 90 | 0x5A | Diagnostic info |
| 100 | 0x64 | Read error |
| 71 | 0x47 | Modem test, NRA connection info |
| 123 | 0x7B | Device info (FW version, serial, etc) |
| 65 | 0x41 | Daily taxation info |
| 64 | 0x40 | Last fiscal entry info |

### F. Date/time

| Cmd | Hex | Operation |
|---|---|---|
| 61 | 0x3D | Set date/time |
| 62 | 0x3E | Read date/time |
| 63 | 0x3F | Display date/time on external display |

### G. Cash operations (служебно въведено / изведено)

| Cmd | Hex | Operation |
|---|---|---|
| 70 | 0x46 | Cash in / cash out |
| 106 | 0x6A | Drawer opening |

### H. Configuration (admin)

| Cmd | Hex | Operation |
|---|---|---|
| 83 | 0x53 | VAT rate programming |
| 96 | 0x60 | Set software password |
| 98 | 0x62 | Programming TAX number |
| 99 | 0x63 | Read TAX number |
| 101 | 0x65 | Set operator password |
| 91 | 0x5B | Programming serial+FM number |
| 66 | 0x42 | Invoice interval |
| 87 | 0x57 | Item groups info |
| 88 | 0x58 | Department info |
| 255 | 0xFF | Parameter read/write (general) |

### I. PLU (item) management — cmd 107 (0x6B)

13 sub-options: P, I, A, D, R, F, L, N, f, l, n, X, x.
Виж раздел 4.55 в PDF, страници 54-65.

### J. Clients DB — cmd 140 (0x8C) [*10]

10 sub-options: I, P, D, R, F, L, N, T, X, x.
Виж раздел 4.69, страници 96-104.

### K. Pinpad — cmd 55 (0x37) — 15 sub-options

1=Void, 2=Copy of last, 3=Copy by type, 4=Copy of all, 5=End of day,
6=Report, 7=Full report, 8=Set date/time, 9=Check pinpad,
10=Check server, 11=Loyalty balance, 12=Get update, 13=After errors,
14=Sale without fiscal receipt, 15=Print receipt after transaction.

### L. EJ (КЛЕН) operations — cmd 125 (0x7D)

6 sub-options: read by line, structured data read, print document,
CSV format read, etc. Виж раздел 4.65, страници 84-87.

### M. Fiscal memory — cmd 126 (0x7E)

11 sub-options: max records, Z reports structured, device ID,
FM number, fiscalization date, TAX number changes, VAT rate
changes, memory resets, NRA registrations/unregistrations, EJ changes.
Виж раздел 4.66.

### N. Service operations — cmd 253 (0xFD)

6 sub-options: enter service password, change password, close EJ,
factory reset, clear NRA errors, send all unsent docs.
**ОПАСНИ — изискват service jumper + password.**

## 9. Payment types в cmd 53 (0x35)

### 9.1 Standard
- 0 = Cash (в брой)
- 1 = Credit card (без pinpad integration)
- 2-7 = Дополнителни methods (програмирани в device)

### 9.2 Card with pinpad
Активира физически POS терминал, чака transaction approval.

### 9.3 Foreign currency
Изисква предварително програмиран exchange rate (cmd 115 / 0x73).

### 9.4 Card with pinpad + transaction data return
Връща authorization code, RRN, и т.н. за съхранение в Odoo.

## 10. Open fiscal receipt — два syntax-а (cmd 48)

### Syntax #1 (legacy)
```
OpCode \t OpPwd \t TillNmb \t Invoice \t
```

### Syntax #2 (с UNS — Unique Sale Number)
```
OpCode \t OpPwd \t NSale \t TillNmb \t Invoice \t
```

`NSale` формат: `LLDDDDDD-CCCC-DDDDDDD` (L=letter, D=digit, C=alphanumeric).
Примери: `DT636533-0020-0010110`.

**Препоръка:** използвай винаги syntax #2 за idempotent retry. Първите
два символа са fiscal device prefix, така че NSale-ите от различни
устройства не се сблъскват.

## 11. Cmd 56 (Close) и cmd 60 (Cancel) семантика

- **Close (0x38)** — нормално приключване. Receipt се записва във FM
  и EJ, send-ва се към НАП server (ако има connectivity).
- **Cancel (0x3C)** — отмяна. Receipt НЕ се записва, но fiscal session
  не се променя. Използвай за error recovery.

Не може да се cancel-не след подаване на cmd 53 (Total payment) —
в този случай receipt вече е fiscalized в EJ.

## 12. Verification examples от PDF

### Open fiscal receipt (cmd 48 syntax #1)

Request hex:
```
01 30 30 33 33 2C 30 30 33 30 31 09 31 09 32 34 09 49 09 05 30 32 3E 3F 03
```

Decoded:
- PRE: `01`
- LEN: `30 30 33 33` → ASCII "0033" → 0x33 → 51 bytes total (51 - 0x20 = 19 bytes content)
- SEQ: `2C` (= 44)
- CMD: `30 30 33 30` → ASCII "0030" → 0x30 → cmd 48
- DATA: `31 09 31 09 32 34 09 49 09` → "1\t1\t24\tI\t"
- PST: `05`
- BCC: `30 32 3E 3F` → ASCII "023?" → 0x023F (verify by sum)
- EOT: `03`

Response hex:
```
01 30 30 33 39 2C 30 30 33 30 30 09 34 37 32 09 04 80 80 88 80 86 9A 80 80 05 30 36 3C 3B 03
```

Decoded:
- DATA: "0\t472\t" (ErrorCode=0, SlipNumber=472)
- STAT: `80 80 88 80 86 9A 80 80`
  - Byte 0 = 0x80 → only bit 7 set → no general errors
  - Byte 1 = 0x80 → no errors
  - Byte 2 = 0x88 → bit 3 set → fiscal receipt is open ✓
  - Byte 3 = 0x80
  - Byte 4 = 0x86 → bits 1, 2 set → TAX# set, Serial+FM set
  - Byte 5 = 0x9A → bits 1, 3, 4 set → FM formatted, fiscalized, VAT set
  - Bytes 6, 7 = 0x80

## 13. Командна таблица — пълна

Виж `command_map.csv` (73 reda).

Phase priority за имплементация:
- Phase 1 (минимум за back-office invoice): 74, 48, 49, 51, 53, 56, 60
- Phase 2 (back-office complete): + 57, 109, 70, 69, 76
- Phase 3 (POS): + 55 (pinpad), 58, 107 (PLU)
- Phase 4 (admin): + 83, 98, 126, 255, 253
