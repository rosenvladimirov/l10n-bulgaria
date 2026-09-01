# -*- coding: utf-8 -*-
"""DEF-116/1б — часовете отстъпват на ГРАФИКА.

`new_weekly_hours` / `new_daily_hours` бяха ВХОД на ДС-то, по който то САМО
намираше календар — първия запис с две съвпадащи числа. Сега графикът се
избира изрично, а часовете се извеждат от него.

🔑 Пренасяме, преди да изтрием: за всяко ДС със записани часове търсим
календара на фирмата, чиито дневни и седмични часове се връзват с тях, и го
записваме в `new_resource_calendar_id`. Така заварените ДС-та не губят
съдържанието си.

⚠️ Пренасянето е по СЪЩОТО съвпадение на два скалара, което поправяме — но
тук то е единствената налична информация. Ако не се намери календар,
стойността се губи явно (лог), а не мълчаливо.

🚨 `old_daily_hours` / `old_weekly_hours` ОСТАВАТ: те са снимката на
подписания документ, не вход.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT column_name FROM information_schema.columns
         WHERE table_name = 'l10n_bg_hr_version_amendment'
           AND column_name IN ('new_daily_hours', 'new_weekly_hours')
    """)
    if len(cr.fetchall()) < 2:
        return

    cr.execute("""
        ALTER TABLE l10n_bg_hr_version_amendment
          ADD COLUMN IF NOT EXISTS new_resource_calendar_id integer,
          ADD COLUMN IF NOT EXISTS old_resource_calendar_id integer
    """)

    # Съвпадението се търси срещу ЯДРЕНИТЕ полета на календара; сборът на
    # присъствията не е достъпен от чист SQL, тъй че се стъпва на
    # `hours_per_day` и `full_time_required_hours` — колкото е знаело и
    # старото търсене.
    cr.execute("""
        UPDATE l10n_bg_hr_version_amendment a
           SET new_resource_calendar_id = c.id
          FROM resource_calendar c, hr_version v
         WHERE a.version_id = v.id
           AND a.new_resource_calendar_id IS NULL
           AND COALESCE(a.new_daily_hours, 0) > 0
           AND (c.company_id = v.company_id OR c.company_id IS NULL)
           AND abs(c.hours_per_day - a.new_daily_hours) < 0.01
           AND (a.new_weekly_hours IS NULL OR a.new_weekly_hours = 0
                OR abs(COALESCE(c.full_time_required_hours, 0)
                       - a.new_weekly_hours) < 0.01)
    """)
    prenes = cr.rowcount

    cr.execute("""
        SELECT count(*) FROM l10n_bg_hr_version_amendment
         WHERE COALESCE(new_daily_hours, 0) > 0
           AND new_resource_calendar_id IS NULL
    """)
    izgubeni = cr.fetchone()[0]

    # Снимката на стария график се пълни от версията — за да не остане
    # празна колона там, където документът вече е активиран.
    cr.execute("""
        UPDATE l10n_bg_hr_version_amendment a
           SET old_resource_calendar_id = v.resource_calendar_id
          FROM hr_version v
         WHERE a.version_id = v.id
           AND a.old_resource_calendar_id IS NULL
    """)

    cr.execute("""
        ALTER TABLE l10n_bg_hr_version_amendment
          DROP COLUMN IF EXISTS new_daily_hours,
          DROP COLUMN IF EXISTS new_weekly_hours
    """)

    _logger.info(
        "DEF-116/1б: пренесени %s ДС-та към график; %s останаха без "
        "съвпадащ календар и часовете им отпадат.", prenes, izgubeni)
    if izgubeni:
        _logger.warning(
            "DEF-116/1б: %s ДС-та със записани часове НЕ намериха календар на "
            "фирмата си. Прегледай ги — графикът им трябва да се избере ръчно.",
            izgubeni)
