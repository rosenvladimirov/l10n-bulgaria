# Bulgaria - Cities and Locations

> Complete database of Bulgarian cities, municipalities,
            and administrative-territorial units with ЕКАТТЕ codes.

**Module:** `l10n_bg_city` | **Version:** 18.0.1.1.0 | **License:** AGPL-3 | **Category:** Localization

## Overview

Bulgaria - Cities and Locations Database
This module provides a comprehensive database of Bulgarian geographic locations,
including cities, villages, municipalities, and administrative structures, fully
integrated with the ЕКАТТЕ (Unified Classifier of Administrative-Territorial and
Territorial Units) national standard.
**Core Features**
-----------------
**ЕКАТТЕ Integration**
~~~~~~~~~~~~~~~~~~~~~~
* Full support for ЕКАТТЕ codes (Единен класификатор на административно-
териториалните и територилните единици)
* Official classification system used by Bulgarian National Statistical Institute
* Unique identification codes for all settlements and administrative units
* Enables compliance with Bulgarian administrative standards

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `base_address_extended`, `contacts` | — |

**External Python packages:** `dbfread`, `requests`

## New models

- `l10n.bg.ekatte.sync`
- `res.city.types`

## Extended models

- `res.city` (inherited)
- `res.country.state` (inherited)

## Views

- `views/l10n_bg_ekatte_sync_views.xml`
- `views/res_city_view.xml`

## Seeded data

- `data/ir_cron_data.xml`
- `data/res.city.cityhall.csv`
- `data/res.city.csv`
- `data/res.city.municipality.csv`
- `data/res.country.state.csv`
- `data/res_city_types.xml`
- `data/res_country_data.xml`
- `data/src`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'l10n_bg_city' or via CLI:
odoo -i l10n_bg_city -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
