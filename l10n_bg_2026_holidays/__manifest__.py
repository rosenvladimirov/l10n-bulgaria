{
    "name": "Bulgaria 2026 - Public Holidays",
    "summary": "БГ официални празници 2026 г. (по чл. 154 КТ) — fixed + Великден 12 април",
    "description": """
Bulgaria 2026 — Public Holidays
================================

Year-stamped data-only module — adds ``resource.calendar.leaves``
records за 2026 г. за всички български официални празници по
чл. 154 КТ. Records са глобални (``resource_id=False``,
``calendar_id=False``) — важат за всеки работен календар.

Module naming convention
------------------------
``l10n_bg_<YYYY>_holidays`` — едно ново module per година. Install-ва
се **в допълнение** на предходните години. Стари records остават;
не може да има конфликт защото датите са различни.

For 2027: copy → ``l10n_bg_2027_holidays``, swap ``2026-`` → ``2027-`` +
update Easter (Великден 2027 = 2 май).

Idempotency
-----------
``post_init_hook`` (в ``__init__.py``) проверява че всички 14 holiday
records за 2026 са създадени; логва липсващи или manual edits, без да
override-ва.

Празници 2026
-------------

**Фиксирани (10):**

* 1 януари — Нова година
* 3 март — Ден на Освобождението
* 1 май — Ден на труда
* 6 май — Гергьовден / Ден на храбростта
* 24 май — Ден на просвета и култура и на славянската писменост
* 6 септември — Ден на Съединението
* 22 септември — Ден на Независимостта
* 24 декември — Бъдни вечер
* 25 декември — Рождество Христово
* 26 декември — Втори ден на Коледа

**Подвижни — Православен Великден 12 април 2026 (4):**

* Велик петък — 10 април
* Велика събота — 11 април
* Великден — 12 април
* Светъл понеделник — 13 април

NOT included
------------
* Заместени дни по чл. 154а КТ (РМС-обявени за връзка с уикенди) — не
  са предвидими, добавят се ръчно при обявяване.
    """,
    "version": "18.0.1.0.1",
    "development_status": "Mature",
    "category": "Localization",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "resource",
    ],
    "data": [
        "data/holidays_2026.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
    "countries": ["BG"],
}
