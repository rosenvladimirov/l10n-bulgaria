# Bulgaria localization Configuration

> This module allows you to install and configure all
        the localization modules related to Bulgaria.

**Module:** `l10n_bg_config` | **Version:** 18.0.8.3.0 | **License:** LGPL-3 | **Category:** Localization

## Overview

Bulgaria Localization Configuration - Core Foundation Module
This is the core configuration module for Bulgarian localization in Odoo, providing
the essential infrastructure and utilities required by all other Bulgarian accounting
and localization modules.
**Core Features**
-----------------
**Configuration Management**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Centralized configuration system for all Bulgarian localization modules
* XML-based configuration templates with dynamic parsing
* Company-level settings for Bulgarian accounting compliance
* Multi-company support with per-company configuration
* Encryption system for sensitive API keys and credentials
**Mixin Architecture (l10n.bg.config.mixin)**

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `account`, `base_vat` | `l10n_bg`, `l10n_bg_ledger`, `l10n_bg_tariff_code` |

**External Python packages:** `xmltodict`, `cryptography`

## New models

- `account.move`
- `account.move.line`
- `l10n.bg.config.mixin`
- `res.partner`

## Extended models

- `account.account.tag` (inherited)
- `account.chart.template` (inherited)
- `ir.module.module` (inherited)
- `res.bank` (inherited)
- `res.company` (inherited)
- `res.config.settings` (inherited)
- `res.country` (inherited)

## Views

- `views/account_account_tag_views.xml`
- `views/account_move_views.xml`
- `views/partner_view.xml`
- `views/res_company_views.xml`
- `views/res_config_view.xml`

## Controllers

- `controllers/blacklist_controller.py`

## Seeded data

- `data/blacklist.enc`
- `data/res_lang_data.xml`
- `data/template`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_config' or via CLI:
odoo -i l10n_bg_config -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
