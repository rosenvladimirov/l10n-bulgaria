"""DEF-140 — поправя UTC границите на летните празници в ЗАВАРЕНИТЕ бази.

Данните са `noupdate="1"`, тоест `-u` НЕ пипа вече създадените записи — а
точно те са сгрешените. Затова миграция.

Какво беше сгрешено: и четиринайсетте записа бяха с офсет +2 (EET), докато
деветте в периода на лятното време са +3 (EEST). При +3 записаният край
`21:59:59 UTC` се чете като `00:59:59` местно на СЛЕДВАЩИЯ ден, тъй че
обхождането ден по ден добавя още един почивен ден.

Пипат се САМО записи, които още носят точно старата (сгрешена) стойност —
ръчно коригираните остават както са.
"""
import logging

_logger = logging.getLogger(__name__)

MODULE = "l10n_bg_2026_holidays"


def _restore_noupdate(cr):
    """Носено от миграцията за 19.0.1.0.1 — не се губи при вдигането.

    Връща `noupdate = TRUE` за записите на модула след презареждането на
    данните, за да са защитени празниците от случайно презаписване занапред
    (клиентски редакции).
    """
    cr.execute(
        "UPDATE ir_model_data SET noupdate = TRUE WHERE module = %s",
        (MODULE,),
    )

# xmlid → (старо date_from, старо date_to, ново date_from, ново date_to)
# Границите са пресметнати през Europe/Sofia, не наум.
SUMMER_HOLIDAYS = {
    "bg_holiday_2026_good_friday":
        ("2026-04-09 22:00:00", "2026-04-10 21:59:59",
         "2026-04-09 21:00:00", "2026-04-10 20:59:59"),
    "bg_holiday_2026_holy_saturday":
        ("2026-04-10 22:00:00", "2026-04-11 21:59:59",
         "2026-04-10 21:00:00", "2026-04-11 20:59:59"),
    "bg_holiday_2026_easter_sunday":
        ("2026-04-11 22:00:00", "2026-04-12 21:59:59",
         "2026-04-11 21:00:00", "2026-04-12 20:59:59"),
    "bg_holiday_2026_easter_monday":
        ("2026-04-12 22:00:00", "2026-04-13 21:59:59",
         "2026-04-12 21:00:00", "2026-04-13 20:59:59"),
    "bg_holiday_2026_labour_day":
        ("2026-04-30 22:00:00", "2026-05-01 21:59:59",
         "2026-04-30 21:00:00", "2026-05-01 20:59:59"),
    "bg_holiday_2026_st_george":
        ("2026-05-05 22:00:00", "2026-05-06 21:59:59",
         "2026-05-05 21:00:00", "2026-05-06 20:59:59"),
    "bg_holiday_2026_education_culture":
        ("2026-05-23 22:00:00", "2026-05-24 21:59:59",
         "2026-05-23 21:00:00", "2026-05-24 20:59:59"),
    "bg_holiday_2026_unification_day":
        ("2026-09-05 22:00:00", "2026-09-06 21:59:59",
         "2026-09-05 21:00:00", "2026-09-06 20:59:59"),
    "bg_holiday_2026_independence_day":
        ("2026-09-21 22:00:00", "2026-09-22 21:59:59",
         "2026-09-21 21:00:00", "2026-09-22 20:59:59"),
}


def migrate(cr, version):
    if not version:
        return
    _restore_noupdate(cr)
    fixed = skipped = missing = 0
    for name, (old_from, old_to, new_from, new_to) in SUMMER_HOLIDAYS.items():
        cr.execute("""
            SELECT res_id FROM ir_model_data
             WHERE module = %s AND name = %s AND model = 'resource.calendar.leaves'
        """, (MODULE, name))
        row = cr.fetchone()
        if not row:
            missing += 1
            continue
        cr.execute("""
            UPDATE resource_calendar_leaves
               SET date_from = %s, date_to = %s
             WHERE id = %s AND date_from = %s AND date_to = %s
        """, (new_from, new_to, row[0], old_from, old_to))
        if cr.rowcount:
            fixed += 1
            continue
        # Не е бил със старата стойност. Две различни причини — разграничават
        # се, за да не изглежда ръчна редакция това, което е нормалният път:
        # `pre-migration` сваля `noupdate`, XML-ът се презарежда и записът вече
        # носи ВЕРНИТЕ граници, преди да стигнем дотук.
        cr.execute("SELECT date_from, date_to FROM resource_calendar_leaves "
                   "WHERE id = %s", (row[0],))
        current = cr.fetchone()
        if current and [str(v)[:19] for v in current] == [new_from, new_to]:
            skipped += 1
        else:
            skipped += 1
            _logger.warning(
                "[%s] DEF-140: %s носи %s — нито старата, нито новата стойност. "
                "Оставен непокътнат (ръчна редакция).", MODULE, name, current)
    _logger.info(
        "[%s] DEF-140: поправени %d летни празника, оставени %d, липсващи %d. "
        "Зимните записи не се пипат — при +2 старите граници са верни.",
        MODULE, fixed, skipped, missing)
