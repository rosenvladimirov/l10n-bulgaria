# Partner Multilang

> Automatic multilingual partner names with intelligent
            transliteration and language detection.

**Module:** `partner_multilang` | **Version:** 18.0.3.0.3 | **License:** AGPL-3 | **Category:** Localization

## Overview

Partner Multilang - Intelligent Transliteration System
This module provides automatic multilingual support for partner, company, and
location data with intelligent language detection and transliteration from
Cyrillic and other non-Latin scripts to Latin characters.
**Core Features**
-----------------
**Automatic Language Detection**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Multi-library language detection with fallback strategy:
1. **Lingua Library** (Primary - Most Accurate)
 - High-precision language detection
 - Supports: Bulgarian, Russian, Serbian, Macedonian, Ukrainian, English
 - Neural network-based detection
 - Best for short texts and names

## Dependencies

| Odoo core | Bulgarian-localization |
|---|---|
| `contacts` | — |

**External Python packages:** `transliterate`, `unidecode`, `lingua`

## New models

- `raw`
- `res.company`
- `res.partner`
- `res.transliterate.mixin`

## Extended models

- `ir.binary` (inherited)
- `res.config.settings` (inherited)
- `res.country.state` (inherited)
- `res.lang` (inherited)

## Views

- `views/res_config_settings_view.xml`
- `views/res_lang_views.xml`

## Installation

```bash
# Add this repository's path to your Odoo addons_path,
# then install via UI Apps → search 'partner_multilang' or via CLI:
odoo -i partner_multilang -d <your_database> --stop-after-init
```

## See also

- Parent repository: [`l10n-bulgaria`](../README.md)

---
*Generated 2026-05-15 from `__manifest__.py` + source layout. Hand-enrich for full handbook coverage.*
