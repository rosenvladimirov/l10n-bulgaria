=======================================
Bulgaria Tariff Code Management (TARIC)
=======================================

.. |badge1| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

|badge1|

This module provides comprehensive tariff code management for Bulgarian companies with integration to the EU TARIC system.

**Table of contents**

.. contents::
   :local:

Features
========

TARIC Integration
-----------------

* Automatic TARIC code detection from HS/CN/Intrastat codes
* Real-time tariff rate lookup from EU TARIC API system
* Local caching mechanism for tariff rates
* Support for multiple countries of origin
* Backward compatibility with HS/CN codes
* Import TARIC data from CIRCABC Excel/CSV files

Product Extensions
------------------

* Tariff code management on products
* Automatic HS code synchronization
* Country of origin tracking
* Tariff rate caching with auto-refresh
* Manual tariff rate update button

Invoice Line Features
---------------------

* Automatic tariff code extraction from various sources
* Manual tariff code override
* Tariff rate computation and caching
* Multi-format code normalization (HS6, CN8, CN10)
* Batch update of tariff rates
* Sync tariff codes to product HS codes

Company Configuration
---------------------

* TARIC API URL configuration
* API enable/disable setting
* Default tariff rate fallback
* Cache duration management
* Multi-company support

TARIC Cache Management
----------------------

* Local database cache for tariff rates
* Import from CIRCABC URL or uploaded file
* Support for Excel (.xlsx) and CSV formats
* Automatic expiry cleanup
* Validity period tracking

Configuration
=============

After installation, configure the module:

1. Go to **Accounting → Configuration → Settings**
2. Scroll to **TARIC Integration** section
3. Enable **Enable TARIC API**
4. Configure:

   * **TARIC API URL**: Default is UK Trade Tariff API (Northern Ireland - uses EU TARIC data)
   * **Cache Duration**: How many hours to cache rates (default: 24)
   * **Default Tariff Rate**: Fallback rate when lookup fails

CIRCABC Data Import
-------------------

To import TARIC data from European Commission CIRCABC:

1. Go to **Accounting → Configuration → TARIC → Import TARIC Data**
2. Choose import method:

   * **Upload File**: Upload Excel (.xlsx) or CSV file
   * **Download from URL**: Enter direct CIRCABC link

3. Click **Import**

Expected file format:

* **CN Code**: 8-10 digit Combined Nomenclature code
* **Country Code**: 2-letter ISO country code
* **Duty Rate**: Percentage rate (with or without % symbol)
* **Description**: Optional goods description
* **Valid From/To**: Optional validity dates

Usage
=====

Product Configuration
---------------------

1. Go to **Inventory → Products → Products**
2. Open a product
3. Go to **Accounting** tab
4. Enter **HS Code** (6-8 digits)
5. The system will automatically:

   * Normalize the code to CN format (8 digits)
   * Fetch tariff rate from EU TARIC
   * Cache the rate
   * Display tariff description

6. Use 🔄 button to manually refresh rate

Invoice Lines
-------------

When creating invoices:

1. Add product to invoice line
2. Tariff code is automatically extracted from:

   * Product HS code (priority)
   * Intrastat code (if available)
   * Line description text
   * Product category

3. Tariff rate is automatically fetched and cached
4. Manual override available in **Information** tab
5. Use **Update Tariff Rates** button to batch refresh
6. Use **🔄 Sync HS Codes** to copy codes back to products

TARIC Cache View
----------------

Monitor and manage cached rates:

1. Go to **Accounting → Configuration → TARIC → TARIC Cache**
2. View all cached entries with:

   * CN code
   * Country of origin
   * Duty rate
   * Validity period
   * Data source (API/CIRCABC/Manual)

3. Filter by:

   * Valid today
   * Source type
   * Country

Technical Details
=================

Code Extraction Patterns
------------------------

The module recognizes codes in various formats:

* ``CN: 85333900``
* ``HS: 853339``
* ``Code: 85333900``
* ``Intrastat: 85333900``
* ``Tariff: 85333900``
* Plain 6-10 digit numbers

Code Normalization
------------------

* **6 digits** (HS): Padded to 8 digits (CN) → ``853339`` → ``85333900``
* **8 digits** (CN): Used as-is → ``85333900``
* **10 digits** (Full): Used as-is → ``8533390000``
* **7 or 9 digits**: Padded with zeros

API Data Sources
----------------

The module uses multiple data sources (priority order):

1. **Local Cache** (``l10n_bg.taric.cache``)
2. **UK Trade Tariff API** (Northern Ireland - uses EU TARIC)

   * Endpoint: ``https://api.trade-tariff.service.gov.uk/xi/api/v2/``
   * Free, public API
   * Real EU TARIC data

3. **Default Rates** by country

EU Countries
------------

Goods from EU member states have 0% tariff rate:

AT, BE, BG, HR, CY, CZ, DK, EE, FI, FR, DE, GR, HU, IE, IT, LV, LT, LU, MT, NL, PL, PT, RO, SK, SI, ES, SE

Default Rates by Country
------------------------

When API lookup fails:

* CN (China): 6.5%
* IN (India): 4.5%
* US (United States): 3.2%
* JP (Japan): 2.1%
* KR (South Korea): 2.5%
* TR (Turkey): 1.8%
* TH (Thailand): 3.0%
* VN (Vietnam): 4.2%
* MY (Malaysia): 3.5%
* ID (Indonesia): 4.0%
* Other: Company default rate

Dependencies
============

External Python Libraries
-------------------------

* ``requests`` - HTTP library for API calls

Odoo Modules
------------

* ``account`` - Accounting core
* ``stock_delivery`` - For HS code field on products

Known Issues / Roadmap
======================

Known Issues
------------

* CIRCABC direct download may require authentication for some files
* API rate limiting may occur with high-volume lookups

Roadmap
-------

* Direct EU TARIC SOAP API integration
* Preferential tariff rates support
* Anti-dumping duties tracking
* Quota management
* Historical rate tracking

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/rosenvladimirov/l10n-bulgaria-ee/issues>`_.

In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed
`feedback <https://github.com/rosenvladimirov/l10n-bulgaria-ee/issues/new?body=module:%20l10n_bg_taric%0Aversion:%2018.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Credits
=======

Authors
-------

* Rosen Vladimirov

Contributors
------------

* Rosen Vladimirov <vladimirov.rosen@gmail.com>

Maintainers
-----------

This module is maintained by Rosen Vladimirov.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is part of the `l10n-bulgaria-ee <https://github.com/rosenvladimirov/l10n-bulgaria-ee>`_ project.

License
=======

This module is licensed under LGPL-3.

References
==========

* `EU TARIC System <https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp>`_
* `UK Trade Tariff API <https://api.trade-tariff.service.gov.uk/>`_
* `CIRCABC <https://circabc.europa.eu/>`_ - European Commission Document Management
* `Combined Nomenclature <https://taxation-customs.ec.europa.eu/customs-4/calculation-customs-duties/customs-tariff/combined-nomenclature_en>`_
