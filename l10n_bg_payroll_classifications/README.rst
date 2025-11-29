=========================================
Bulgarian HR Payroll Classifications
=========================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-OCA%2Fl10n--bulgaria-lightgray.png?logo=github
    :target: https://github.com/OCA/l10n-bulgaria/tree/18.0/l10n_bg_payroll_classifications
    :alt: OCA/l10n-bulgaria

|badge1| |badge2| |badge3|

**l10n_bg_payroll_classifications** is an Odoo module that provides Bulgarian localization for HR and payroll classifications. The module includes complete management of NCOP (National Classification of Occupations and Positions) and Economic Activities (KID) with MOD rates for compliance with Bulgarian labor regulations.

**Table of contents**

.. contents::
   :local:

Features
========

NCOP (National Classification of Occupations and Positions)
----------------------------------------------------------

* **Complete NCOP hierarchy** - Management of NCOP 2011 structure
* **Professional groups** - Organization by classes, sub-classes, groups and unit groups
* **Qualification grouping** - Automatic linking with MOD categories
* **Education requirements** - Definition of minimum education levels
* **Skills and experience** - Description of requirements for each position
* **Employee integration** - Connection with positions in HR module

Economic Activities (KID)
------------------------

* **KID classification structure** - Complete hierarchy (Sections, Divisions, Groups, Classes)
* **MOD rates by qualification** - Minimum insurance income for 8 qualification groups:

  - Managers
  - Specialists
  - Technicians
  - Clerks (Administrative support personnel)
  - Service Workers
  - Skilled Workers
  - Machine Operators and Assemblers
  - Elementary Occupations

* **TZPB rates** - Work Accident and Occupational Disease insurance rates
* **Validity periods** - Management of validity dates for rate changes

Technical Specifications
========================

Models
------

**bg.ncop.classification**
  Model for NCOP classifications with the following key fields:

  * ``code`` - 8-digit NCOP code
  * ``name`` - Position name (translatable)
  * ``level`` - Hierarchical level (class, sub-class, group, unit group)
  * ``qualification_group`` - Qualification group for MOD calculations
  * ``education_level`` - Minimum education level
  * ``skills_requirements`` - Skills requirements
  * ``experience_years`` - Required years of experience

**bg.mod.economic.activity**
  Model for economic activities with MOD rates:

  * ``code`` - KID code
  * ``name`` - Activity name (translatable)
  * ``level`` - Level in hierarchy (section, division, group, class)
  * ``mod_*`` fields - MOD rates for each qualification group
  * ``tzpb_rate`` - TZPB rate in percentage
  * ``date_from/date_to`` - Validity period

Data Files
----------

* **bg_ncop_classifications.csv** - Core NCOP classifications
* **bg_mod_economic_activities.csv** - Economic activities with MOD rates
* **List_Of_Occupations_01_01_2025.csv** - Current list of occupations
* **Structure_NKPD_2011_01_01_2022.csv** - NCOP 2011 structure

Views
-----

* **Menu structure** - Bulgarian HR menu with appropriate sections
* **NCOP views** - Tree and form views for NCOP classifications
* **KID views** - Management of economic activities and MOD rates

Use Cases
=========

This module is essential for Bulgarian companies that need to:

* **Comply with labor legislation** - Proper classification of employees according to NCOP
* **Insurance accounting** - Calculate correct MOD amounts by qualification groups
* **TZPB insurance** - Apply correct rates for work accidents
* **HR management** - Structured management of positions and professions
* **Payroll accounting** - Integration with payroll systems for the Bulgarian market

The module is particularly useful for:

* Medium and large enterprises with diverse professions
* HR consulting firms
* Accounting firms serving multiple clients
* Companies working with public procurement (NCOP requirement)

Installation
============

1. Copy the module to the ``addons`` directory of Odoo
2. Update the module list
3. Install ``l10n_bg_payroll_classifications``
4. Data will be loaded automatically

Configuration
=============

1. Go to **Human Resources > Configuration > Bulgarian Classifications**
2. Review and update NCOP classifications as needed
3. Configure MOD rates in **Human Resources > Configuration > Economic Activities**
4. Link employees with appropriate NCOP positions

Compatibility
=============

* Odoo 18.0+
* Depends on: ``base``, ``hr``, ``hr_contract``
* Works well with other Bulgarian L10N modules

Bug Tracker
===========

Bugs are tracked on GitHub Issues. In case of trouble, please check there if your issue has already been reported.

Credits
=======

Authors
-------

* Your Company

Contributors
-----------

- Developer (vladimirov.rosen@gmail.com)

License
=======

This module is distributed under the AGPL-3 license. See the LICENSE file for details.

Maintainers
===========

This module is part of the l10n-bulgaria project and is maintained by the community.
