{
    "name": "Partner Multilang",
    "version": '19.4.2.0.2',
    "license": "AGPL-3",
    "category": "Localization",
    "author": "Rosen Vladimirov, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/partner-contact",
    "summary": """
            Automatic multilingual partner names with intelligent
            transliteration and language detection.""",
    "description": """
Partner Multilang - Intelligent Transliteration System
======================================================

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

2. **Langdetect** (Secondary - Fast)
 - Quick language identification
 - Broader language support
 - Statistical approach
 - Fallback when Lingua unavailable

3. **Unknown Language Handling**
 - Graceful degradation when detection fails
 - Fallback to user's language context
 - Smart text length validation (minimum 3 characters)

**Intelligent Transliteration**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Two-tier transliteration system:

**Tier 1: Language-Specific Transliteration**
* **transliterate library** for precise conversion
* Language-specific rules:
- Bulgarian (bg): ISO 9 transliteration
- Russian (ru): GOST 7.79 System B
- Macedonian (mk): Scientific transliteration
- Serbian (sr): Serbian Latin
- Ukrainian (uk): National system
- Belarusian (be): Scholarly system

**Tier 2: Universal Fallback**
* **unidecode library** for any Unicode text
* ASCII-compatible output
* Works for all scripts: Cyrillic, Greek, Arabic, Chinese, etc.
* Ensures data compatibility across systems

**Translatable Fields**
~~~~~~~~~~~~~~~~~~~~~~~

**Partner/Contact Fields:**
* `name` - Partner/Contact name
* `street` - Street address line 1
* `street2` - Street address line 2
* `city` - City name
* `function` - Job position/title
* `company_name` - Company name
* `commercial_company_name` - Commercial company name

**Company Fields:**
* `name` - Company name
* `street` - Company street address
* `street2` - Additional address line
* `city` - Company city
* Language field support

**Country/State:**
* State names with translation support

**Mixin Architecture**
~~~~~~~~~~~~~~~~~~~~~~
**res.transliterate.mixin** - Abstract model providing:
* Automatic field detection
* Context-aware transliteration
* Create/Write method hooks
* View ordering by language
* Extensible field list via `_get_transliterate_fields()`

Inherited by:
* `res.partner` - Partners and contacts
* `res.company` - Companies
* Any model requiring multilingual names

**Language Configuration**
~~~~~~~~~~~~~~~~~~~~~~~~~~
Per-language transliteration control:
* `transliterate` field on `res.lang` model
* Enable/disable per language
* Affects automatic transliteration behavior
* Configurable via Language settings

**Multi-Language Search**
~~~~~~~~~~~~~~~~~~~~~~~~~
Enhanced search capabilities:

**JSONB Translation Search:**
* Searches across all active language translations
* Leverages PostgreSQL JSONB operators
* Syntax: `field_name->>'{lang_code}'`
* Automatic domain expansion for all languages

**Smart Name Search:**
```python
_name_search() enhancements:
- Detects search fields from domain
- Expands to multi-language fields
- Searches both base field and translations
- Default fields: name, company_name, commercial_company_name
```

**Search Performance:**
* Language code caching
* Efficient domain construction
* Minimal database queries
* Operator support: '=', 'ilike', etc.

**Automatic Data Processing**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**On Create:**
1. Detect source language from text
2. Store original text in detected language
3. Generate English transliteration if from Cyrillic
4. Save both versions for multi-language access

**On Write:**
1. Check if field is being updated
2. Detect language of new value
3. Update translation in source language
4. Update English transliteration
5. Skip if `update_lang` context flag set

**Context Awareness:**
* Respects user's language (`self.env.user.lang`)
* Language-specific view rendering
* Proper field ordering by language
* Translation loading based on context

**View Enhancements**
~~~~~~~~~~~~~~~~~~~~~
Dynamic view modifications:

**List/Tree Views:**
* Automatic ordering by user's language
* JSONB field ordering: `name->>'{lang_code}'`
* Applies to tree and kanban views
* Maintains sort consistency

**Form Views:**
* Translatable char fields
* Context-sensitive display
* Language switcher support

**Technical Implementation**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Language Mapping:**
```python
LANGUAGE_MAPPING = {
  'bg': 'bg',  # Bulgarian
  'ru': 'ru',  # Russian
  'mk': 'mk',  # Macedonian
  'sr': 'sr',  # Serbian
  'uk': 'uk',  # Ukrainian
  'be': 'be',  # Belarusian
}
```

**Detection Priority:**
1. User context language
2. Lingua automatic detection
3. Langdetect fallback
4. Unknown language handling

**Transliteration Flow:**
```
Input Text → Language Detection →
→ Language-specific transliteration (if available) →
→ Unidecode fallback →
→ ASCII output
```

**External Dependencies**
~~~~~~~~~~~~~~~~~~~~~~~~~
Required Python packages:

1. **transliterate**
 - Language-specific Cyrillic transliteration
 - ISO standards support
 - Reversible transliteration

2. **unidecode**
 - Universal Unicode to ASCII
 - Fallback for all scripts
 - Lightweight and fast

3. **lingua**
 - Advanced language detection
 - Neural network-based
 - High accuracy for short texts

Optional (fallback):
* **langdetect** - Alternative language detection

**Use Cases**
~~~~~~~~~~~~~

**International Business:**
- Partner names in native scripts (Cyrillic, etc.)
- Automatic Latin transliteration for international use
- Searchable in both native and Latin forms
- Email and export compatibility

**Bulgarian Companies:**
- Store names in Bulgarian (Cyrillic)
- Automatic English transliteration
- Bank transfer compatibility
- International invoicing

**Multi-national Partners:**
- Russian partners with Cyrillic names
- Ukrainian suppliers
- Serbian customers
- Proper name representation in all contexts

**Address Localization:**
- City names in native language
- Street names transliterated
- Postal compatibility
- Delivery label generation

**Database Integration:**
- Export to ASCII-only systems
- API compatibility
- International data exchange
- Legacy system integration

**Configuration & Setup**
~~~~~~~~~~~~~~~~~~~~~~~~~

**Enable Transliteration:**
1. Navigate to Settings → Translations → Languages
2. Select language (e.g., Bulgarian)
3. Check "Transliterate" field
4. Save

**Per-Model Customization:**
Override `_get_transliterate_fields()`:
```python
@api.model
def _get_transliterate_fields(self):
  res = super()._get_transliterate_fields()
  return res + ['custom_field1', 'custom_field2']
```

**Hooks System**
~~~~~~~~~~~~~~~~
* `pre_init_hook` - Pre-installation setup
* `post_init_hook` - Post-installation data migration
* `post_load_hook` - Runtime initialization

**Benefits**
~~~~~~~~~~~~
* **Automatic** - No manual transliteration needed
* **Intelligent** - Language detection built-in
* **Flexible** - Multiple transliteration libraries
* **Searchable** - Find partners in any language
* **Compatible** - ASCII output for legacy systems
* **Extensible** - Easy to add custom fields
* **Performance** - Optimized search with caching
* **Standard-compliant** - Uses ISO transliteration standards

**Technical Advantages**
~~~~~~~~~~~~~~~~~~~~~~~~
* **PostgreSQL JSONB** - Efficient multi-language storage
* **Mixin pattern** - Reusable across models
* **Lazy loading** - Translation on demand
* **Context preservation** - Language-aware operations
* **View inheritance** - Clean XPath-based customization
* **Error handling** - Graceful fallbacks at every level

**Integration Points**
~~~~~~~~~~~~~~~~~~~~~~
Essential for Bulgarian localization stack:
* **l10n_bg_config** - Core configuration
* **l10n_bg_city** - City name transliteration
* **l10n_bg_address_extended** - Address fields
* **l10n_bg_reports** - Report generation
* **l10n_bg_tax_admin** - Partner data in reports

**Limitations & Notes**
~~~~~~~~~~~~~~~~~~~~~~~
* Minimum 3 characters for language detection
* English language bypasses transliteration
* One-way transliteration (no reverse mapping)
* Context flag `update_lang` prevents recursion
* Requires PostgreSQL for JSONB support

**Performance Considerations**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Language code caching per search
* Optimized domain construction
* Minimal overhead on create/write
* Efficient JSONB queries
* View ordering with indexes

**Future Enhancements**
~~~~~~~~~~~~~~~~~~~~~~~
* Additional Cyrillic languages (Kazakh, Mongolian)
* Chinese/Japanese romanization
* Arabic transliteration
* Configurable transliteration standards
* Batch processing tools
* Data migration utilities

**Note**: This module is essential for any Odoo installation dealing with
non-Latin script partners (Cyrillic, Greek, Arabic, etc.), providing seamless
international compatibility while preserving native language data.
  """,
    "external_dependencies": {
        "python": [
            "transliterate",
            "unidecode",
            "lingua",
        ]
    },
    "depends": [
        "base",
        "contacts",
    ],
    "data": [
        "views/res_lang_views.xml",
        "views/res_config_settings_view.xml",
    ],
    'images': [
        'static/description/banner.png',
    ],
    "demo": [],
    "installable": True,
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
    'uninstall_hook': 'uninstall_hook',
}
