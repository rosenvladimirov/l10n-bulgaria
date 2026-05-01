# l10n_bg_fiscal_printer_datecs_pm

Direct Python driver за Datecs PM Communication Protocol v2.11.4 (FP-700 MX и
сродни) в Odoo 18. Покрива back-office и POS сценарии без зависимост от
ErpNet.FP.

> **Status:** Alpha — Phase 1 (frame protocol + status/errors + minimum viable
> commands за back-office invoice печат). За roadmap виж `docs/ARCHITECTURE.md`.

## Топологии

| `connection_type` | Сценарий |
|---|---|
| `serial` | Локален Odoo + RS232/USB device (single-shop on-prem) |
| `tcp` | Cloud Odoo + TCP printer през VPN (multi-shop) |
| `agent` | Cloud Odoo + локален Python IoT agent (legacy serial-only device + cloud) |

## Структура

```
l10n_bg_fiscal_printer_datecs_pm/
├── docs/                # Specification (PROTOCOL_REFERENCE, command_map, etc.)
├── drivers/             # Pure-Python protocol layer (no Odoo imports)
│   ├── frame.py         # Frame envelope encode/decode
│   ├── codec.py         # CP-1251 ↔ str
│   ├── status.py        # 8-byte status → FiscalStatus
│   ├── errors.py        # ErrorCode → FiscalError
│   ├── commands.py      # Opcode constants (per command_map.csv)
│   ├── transport*.py    # serial / tcp / agent transports
│   └── pm_v2_11_4.py    # High-level facade
├── models/              # Thin Odoo wrapper layer
├── security/, views/    # Standard Odoo
├── tests/               # pytest-compatible (drivers/) + Odoo TransactionCase
└── i18n/bg.po           # Български преводи на error messages
```

## Архитектурни инварианти

1. `drivers/` е pure-Python — не импортира `odoo.*`
2. Транспортите са взаимозаменяеми (един `Transport` ABC)
3. Frame layer е stateless; sequence number се подава отвън
4. Session/state живее в Odoo моделите, не в драйвера
5. Никога не блокирай Odoo worker thread > 60s

Виж `CLAUDE.md` за full developer guide и `docs/ARCHITECTURE.md` за rationale.

## Тестване

```bash
cd l10n_bg_fiscal_printer_datecs_pm
python -m pytest tests/ -v
ruff check .
ruff format --check .
```

## Не е в scope

- WebSerial/WebUSB direct browser driver
- ErpNet.FP integration → виж `l10n_bg_erp_net_fp`
- Tremol/Eltrade/Daisy support → отделни sibling модули

## Licensing

LGPL-3.0 or later. Communication Protocol © Datecs Ltd. — свободен за писане
на драйвери (чл. 2 от PDF-а).
