# -*- coding: utf-8 -*-
"""Работните дни на месеца — ЕДНА дефиниция за всички слоеве.

Това е донорският слой по DEF-154. Числото „работни дни в месеца" се смяташе на
четири различни места и по три различни начина:

  · `l10n.bg.payroll.register` (ТРЗ) — делнични МИНУС празници ✅
  · ГД мостовете — същото, през същите два примитива ✅
  · `_working_days_in_month` в УП-3 — делнични, БЕЗ да вади празниците ❌
  · `_l10n_bg_month_working_days` в гарда по DEF-142 — също делнични ❌

Вярната дефиниция е първата и тя е доказана срещу 1415 приети от НАП реда:
седем от седем месеца съвпадат, и по дни, и по часове. Нормата е НСОРЗ чл. 18,
ал. 1 — знаменателят са работните дни БЕЗ официалните празници.

## Защо тук

Модулът е LGPL-3 и е достъпен от ТРЗ, ГД, НАП и ЛС слоя — проверено по
транзитивното затваряне на зависимостите. Дефиницията е примитив над
`resource.calendar` на самото ядро, не ТРЗ логика, тъй че мястото ѝ е в общия
слой, а не в който и да е от четирите.

## Защо мек lookup вместо зависимост

`resource` НЕ се добавя в `depends`. Модулът е базов и се инсталира в бази без
кадри; твърда зависимост би ги повлякла без нужда. При липсващ `resource`
методите връщат делнични дни — най-доброто, което може да се каже, без да се
знае за празници. Същият шаблон, който `l10n_bg_civil_base` вече ползва за
`hr.rule.parameter`.
"""
import calendar as _cal
from datetime import date, datetime, time, timedelta

import pytz

from odoo import api, models


class L10nBgWorkCalendarMixin(models.AbstractModel):
    _name = 'l10n.bg.work.calendar.mixin'
    _description = 'Bulgarian working-days calendar helpers'

    @api.model
    def _l10n_bg_public_holidays(self, cal, date_from, date_to):
        """Датите на официалните празници в ``[date_from, date_to]``.

        Глобалните ``resource.calendar.leaves`` (без ресурс) за този календар
        или за всички. Броят се като неработни дни.

        ⚠️ ``date_from``/``date_to`` на записа са UTC. Прочетени с ``.date()``
        без конверсия, те изместват празника с един ден назад за всяка зона
        източно от UTC: 31 декември се пази като 2025-12-30 22:00 UTC и излиза
        като 30-и. Затова се конвертира към зоната на календара ПРЕДИ ``.date()``.
        """
        days = set()
        if not (cal and date_from and date_to):
            return days
        Leaves = self.env.get('resource.calendar.leaves')
        if Leaves is None:
            return days
        holidays = Leaves.sudo().search([
            ('resource_id', '=', False),
            ('calendar_id', 'in', [cal.id, False]),
            ('date_from', '<=', datetime.combine(date_to, time.max)),
            ('date_to', '>=', datetime.combine(date_from, time.min)),
        ])
        tz = pytz.timezone(getattr(cal, 'tz', None) or 'Europe/Sofia')
        for holiday in holidays:
            local_from = holiday.date_from.replace(tzinfo=pytz.UTC).astimezone(tz)
            local_to = holiday.date_to.replace(tzinfo=pytz.UTC).astimezone(tz)
            day = max(local_from.date(), date_from)
            last = min(local_to.date(), date_to)
            while day <= last:
                days.add(day)
                day += timedelta(days=1)
        return days

    @api.model
    def _l10n_bg_works_on(self, cal, day, holidays=None):
        """Работен ден по графика И който НЕ е официален празник.

        Празникът е неработен по чл. 154 КТ: не яде работодателски болничен ден
        и не „чупи" залепването на съседни болнични.
        """
        if holidays and day in holidays:
            return False
        return bool(cal and cal._works_on_date(day))

    @api.model
    def _l10n_bg_month_work_days(self, company, year, month):
        """Работните дни на месеца — делнични МИНУС официалните празници.

        Фирменият вариант: стъпва на календара на компанията, не на конкретно
        лице. Ползва се от местата, които работят върху декларация, а не върху
        фиш.

        Канонът от приетите файлове (1415 реда, 8 файла, 12.2025–06.2026):

            12/2025  23 делнични − 4 празника = 19
            01/2026  22 − 2 = 20      02/2026  20 − 0 = 20
            03/2026  22 − 1 = 21      04/2026  22 − 2 = 20
            05/2026  21 − 3 = 18      06/2026  22 − 0 = 22

        Септември 2026 е 20, не 22 — точно разликата, която прави DEF-154.
        """
        cal = (company.resource_calendar_id
               if company else False) or self.env.company.resource_calendar_id
        year, month = int(year), int(month)
        first = date(year, month, 1)
        last = date(year, month, _cal.monthrange(year, month)[1])
        span = range((last - first).days + 1)
        if not cal:
            # Без календар: Пн–Пт, без да се знае за празници.
            return sum(1 for d in span
                       if (first + timedelta(days=d)).weekday() < 5)
        holidays = self._l10n_bg_public_holidays(cal, first, last)
        return sum(1 for d in span
                   if self._l10n_bg_works_on(
                       cal, first + timedelta(days=d), holidays))
