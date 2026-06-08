{
    "name": "Bulgaria 2026 - Payroll Classifications (МОД EUR + НКПД changes)",
    "summary": "2026: МОД stъvnostъm в EUR (÷1.95583) + audit на НКПД промени",
    "description": """
Bulgaria 2026 — Payroll Classifications
========================================

Year-stamped data module — мигрира МОД stoinostite по икономическа
дейност от лева (2025) към евро (2026), без да губи историческите
records.

Module naming convention
------------------------
``l10n_bg_<YYYY>_classifications`` — едно ново module per година.
Install-ва се в допълнение на предходните години.

Behaviour (post_init_hook)
--------------------------
1. **МОД миграция BGN → EUR**: за всеки активен
   ``bg.hr.payroll.economic.activity`` record с
   ``date_from <= 2025-12-31`` и ``date_to=False``:
     a. set ``date_to = '2025-12-31'`` (close historical record)
     b. clone the record with ``date_from='2026-01-01'`` and всички
        ``mod_*`` стойности конвертирани в EUR (÷ 1.95583, round 2)
2. **НКПД промени**: 2026 г. няма обявени промени от НСИ за NCOP-2011
   nomenclature. Hook log-ва "no NCOP changes for 2026".
3. Идемпотентен: re-install не дублира records (skip ако вече има
   record с ``date_from='2026-01-01'`` за същия КИД).

For 2027
--------
Copy → ``l10n_bg_2027_classifications``. Промени:
* Update YEAR константа в ``__init__.py``
* Set ``EUR_CONVERSION_NEEDED = False`` (вече е в EUR)
* Update mod_* values само ако РМС обяви промени (МОД обикновено е
  *замразен* за няколко години)

Reference
---------
* РМС № 243 от 13.11.2025 (МРЗ + МОД политика 2026)
* ЗВЕРБ — фиксиран курс 1 EUR = 1.95583 BGN
* НСИ NCOP-2011 — последна revision 2011 г.
    """,
    "version": "19.0.1.0.0",
    "development_status": "Mature",
    "category": "Localization",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "l10n_bg_payroll_classifications",
    ],
    "data": [],
    "post_init_hook": "post_init_hook",
    # DEF-22: RETIRED. Механичната BGN÷1.95583 конверсия НЕ съответства на
    # ЗБДОО 2026 (законодателят определи НОВИ EUR стойности, не конвертирани) +
    # broken parent-chain clone (новите записи сочеха към старите BGN записи).
    # Коректните EUR стойности вече са в l10n_bg_payroll_classifications/
    # data/bg_mod_values_noupdate.xml (noupdate=0). НЕ инсталирай — ще повреди
    # вече-коректната база. Запазен само за git история.
    "installable": False,
    "auto_install": False,
    "countries": ["BG"],
}
