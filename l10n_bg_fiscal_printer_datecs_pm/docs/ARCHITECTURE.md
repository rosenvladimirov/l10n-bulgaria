# Архитектурен план — `l10n_bg_fiscal_printer_datecs_pm`

> Стратегически документ. Защо точно така е направен модулът,
> какви компромиси има, и какво следва.

## Цел

Direct Python driver за Datecs PM Communication Protocol v2.11.4
(новото поколение Datecs fiscal devices, основно FP-700 MX) в Odoo 18,
покриващ както back-office (фактуриране, MRP), така и POS (retail)
сценарии, без зависимост от ErpNet.FP.

## Защо отделен модул, не extension на `l10n_bg_erp_net_fp`

`l10n_bg_erp_net_fp` е тънък HTTP/JSON клиент към ErpNet.FP сървър —
самият протокол живее в C# upstream. Този новият модул сменя цялата
философия:

- **Pure Python имплементация** — без C# Docker dependency
- **Без HTTP hop** — директна serial/TCP комуникация
- **Stateless transactions** — Odoo управлява state, не external service
- **Testable in CI** — pure-python драйвер се тества с mock устройство

Двата модула съществуват **паралелно**. Клиентът избира кой да инсталира.
Дълъг term няма миграция — old hardware остава на ErpNet.FP драйвера,
new hardware (PM) идва в новия модул.

## Топология за POS — поддръжка за всичките три

POS deployment-ите имат различни constraint-и. Модулът поддържа три
топологии чрез единен `connection_type` selector на `l10n.bg.fp.device`:

### Topology A: локален Odoo + serial device

```
[PC в магазина]
   ├── Odoo
   └── /dev/ttyUSB0 ── RS232/USB ── [Datecs FP-700 MX]
```

- Латентност: < 50ms (директна serial)
- Деплоймент: ~95% от single-shop българския SME пазар
- Sample клиенти: малки магазини, кафенета, B2B office с касов апарат

### Topology B: cloud Odoo + TCP printer през VPN

```
[Cloud Odoo на VPS]
       │
   OpenVPN/WireGuard tunnel
       │
[Магазин LAN]
   └── 192.168.x.y:9100 ── [Datecs FP-700 MX TCP/IP]
```

- Латентност: 50-200ms (зависи от VPN quality)
- Деплоймент: твоят Konex-Tiva pattern, replicate-ваш за multi-shop
- **Изисква** TCP-capable модел (FP-700 MX го поддържа според Datecs spec)
- Печели от твоята вече-готова OpenVPN инфраструктура

### Topology C: cloud Odoo + локален Python IoT agent

```
[Cloud Odoo]
    │
  HTTPS / WebSocket
    │
[Shop machine]
   ├── l10n_bg_fp_iot_agent (Python service)
   └── /dev/ttyUSB0 ── [Datecs FP-700 MX serial-only]
```

- Латентност: 100-300ms (HTTP roundtrip)
- За когато device е **само serial/USB** и shop няма VPN
- Това на практика е "ErpNet.FP в Python" — приемаш го осъзнато
- IoT agent е **отделен пакет**, не Odoo addon: `pip install l10n-bg-fp-iot-agent`

### Решение по топология във време на запис на receipt

Селекцията се прави **един път, при device config**, не на runtime.
Cross-topology fallback не се поддържа — ако VPN падне, не се
превключва автоматично към agent. Това е съзнателно: fiscal операции
изискват deterministic behavior.

## Core design принципи

### 1. Driver layer = pure Python, no Odoo

```
drivers/
├── transport_serial.py    # implements Transport ABC via pyserial
├── transport_tcp.py       # implements Transport ABC via socket
├── transport_agent.py     # implements Transport ABC via HTTP+JWT
├── frame.py               # encode/decode Datecs frame envelope
├── codec.py               # CP-1251 ↔ Python str
├── status.py              # 8-byte status → FiscalStatus dataclass
├── errors.py              # ErrorCode int → FiscalError(code, name, msg)
├── commands.py            # opcode constants и parameter schemas
└── pm_v2_11_4.py          # high-level facade, command-level API
```

Защото:
- Може да се тества с pure pytest, без Odoo registry
- Може утре да се изнесе като самостоятелен PyPI пакет ако треябя
- Ясна separation of concerns: protocol logic ≠ business logic
- Свободно се reuse-ва в IoT agent-а (същият Python код, различен entry point)

### 2. Odoo layer = thin wrapper

```
models/
├── fiscal_device.py       # l10n.bg.fp.device — connection config
├── fiscal_session.py      # active fiscal session (Z-cycle tracking)
├── fiscal_receipt.py      # receipt record + audit trail
├── fiscalization_log.py   # raw frame log (compliance)
├── pos_config.py          # link pos.config → fiscal_device
├── pos_session.py         # auto-X on open, auto-Z on close
└── account_move.py        # invoice → fiscal action
```

Odoo моделите **не знаят** за бит-нивата, frames, и serial. Те
извикват high-level facade методи: `device.open_receipt(...)`,
`device.add_sale_line(...)`, `device.total_with_payment(...)`.

### 3. Фискалните операции са audit-log-вани

Всеки изпратен и получен frame се запазва в `l10n.bg.fp.frame.log`
(append-only, indexed by receipt_id, timestamp). Това е **compliance
изискване** за БГ Наредба Н-18, не debug feature. Не се изтрива при
GDPR data subject requests — fiscal records са exempt.

### 4. Idempotent retry semantics

Всяка fiscal операция има **уникален unique_sale_number** (cmd 48
syntax #2). Това позволява host да retry-не след network glitch
без device да изпълни командата два пъти. Driver layer използва
SEQ number за low-level retry; high-level layer използва UNS за
business-level retry.

## Open architectural decisions (изискват твоя input)

### D1: Python версия таргет

PM v2.11.4 имплементацията е modern Python (dataclasses, type hints,
async optional). Кой минимум поддържаме?

- Python 3.10+ (Odoo 18 default) — препоръчително
- Python 3.9 (за ssh-only deployment-и) — повече работа за compat
- Python 3.11+ (StrEnum, enhanced typing) — премахва съвместимостта

### D2: Sync vs Async

Driver-ът може да е synchronous (по-проста интеграция с Odoo ORM)
или async (по-чисто за TCP/agent транспорти).

Препоръка: **sync default + asyncio compat layer** за future-proofing.
Odoo workers са sync, но queue_job се ориентира към async.

### D3: Receipt model — извличаме ли в `_base`?

Тек-day избрахме монолитен модул, не base+driver. Но receipt модел
вероятно ще се повтаря в Tremol/Daisy/etc драйвери. Когато дойде
втори vendor, ще извлечем `l10n_bg_fiscal_printer_base`.

**Не extract-вай early** — wait for second use case.

### D4: SAF-T integration timing

Този модул генерира fiscal receipt data. SAF-T export pipeline
(пo твой memory: най-спешна compliance дупка от Jan 2026) консумира
тези данни. Дали сега да добавим SAF-T fields в receipt model, или
по-късно?

Препоръка: **сега**. Receipt schema migration е скъпа, добавянето на
fields е cheap. Дори ако `l10n_bg_saf_t` още не съществува, fields-те
са no-op докато не дойде той.

## Phase plan

| Phase | Scope | Деливер | Зависимости |
|---|---|---|---|
| 1 | Frame protocol + status + errors + mock device | drivers/ покрит с тестове | — |
| 2 | Phase 1 commands (74, 48, 49, 51, 53, 56, 60) | minimal back-office invoice печат работи | Phase 1 |
| 3 | Phase 2 commands (57, 109, 70, 69) | пълен back-office — invoice, duplicate, cash ops, X/Z | Phase 2 |
| 4 | POS frontend integration (OWL компоненти + JSON-RPC) | retail POS работи в Topology A | Phase 3 |
| 5 | TCP transport + Topology B | multi-shop deployments | Phase 4 |
| 6 | IoT agent (отделен PyPI) + Topology C | full topology coverage | Phase 5 |
| 7 | Phase 3-4 commands (PLU, pinpad, VAT prog) | feature-complete за Datecs PM | Phase 4 |
| 8 | NRA registration cmds (71, 7E sub-opts, 72 fiscalization) | пълна compliance | Phase 7 |

Phase 1-3 = MVP. Phase 4 е POS unlock. Phase 5-6 = enterprise.
Phase 7-8 = compliance closing.

## Какво НЕ е в scope

- Други Datecs модели от X-серията (DP-25X, FMP-350X и т.н.) — те
  имат различен протокол (ISL), този модул е само PM
- Други vendor-и (Tremol, Daisy, Eltrade) — отделни sibling addons
- Generic POS hardware периферия — Odoo IoT base покрива тези
- WebSerial/WebUSB direct browser driver — POS винаги минава през
  backend (или agent в Topology C)
- Migration tool от ErpNet.FP — двата модула съществуват паралелно

## Risk register

1. **Datecs PDF има typo-та** — открихме един (cmd 203 listed като
   0xCA, всъщност е 0xCB). Възможно е да има още. Mitigation: всички
   командни опкоди се verify-ват срещу действителен device replay
   преди ship.

2. **CP-1251 кодиране не е документирано explicitly** — приемаме CP-1251
   на база на индустриален стандарт за БГ fiscal devices. Mitigation:
   Phase 1 включва empirical test с реален device, log-ваме байтовете,
   корекция ако е различно.

3. **NRA server connectivity poll-ване** — cmd 0x47 sub-option 3 е
   единственият начин да знаем дали device може да push-ва към НАП.
   При downtime на НАП сървърите, fiscal device entered блокирано
   състояние след N часа. Това трябва да се мониторира на ниво
   `l10n.bg.fp.device.status_cron`.

4. **Service mode flag (0x4D = ERR_DEVICE_IN_SERVICE_MODE)** — ако
   технически техник е в service режим, всички cmds fail-ват. Не е
   bug, не е recoverable от наша страна. UX трябва да го обясни ясно.

5. **POS workflow assumes single fiscal device per pos.config** — ако
   клиентът иска redundant fiscal devices с failover, scope creep.
   За сега: 1:1 mapping.
