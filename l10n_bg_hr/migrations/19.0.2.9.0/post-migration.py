# -*- coding: utf-8 -*-
"""Заварените проценти по версии → решения в историята на ТЕЛК.

Дотук трайно намалената работоспособност живееше като процент върху версията.
Новият модел `l10n_bg.telk.decision` държи историята, но стартира празен —
затова тук се пренася каквото има, инак информацията остава само в стария вид
и бутонът „Приложи решението" не намира какво да приложи.

Как се чете историята от версиите: версиите на един служител се минават по
дата и ВСЯКА ПРОМЯНА на процента ражда ново решение. Периодът на предишното
се затваря в деня преди началото на следващото — гардът за застъпване иска
най-много едно действащо решение към дата.

🚨 Единицата се сменя: версията носи ДРОБ (0,51), а пренесеният модел иска
ЦЯЛО число (51) — полето му е Integer с гард за 1..100. Стойност над 1 се
приема за вече процент; заварените данни носят и двете форми.

🚨 Не се пренасят нулите: процент 0 значи „няма решение", а не „решение с
нула на сто". Не се пренася и вече пренесеното — миграцията е идемпотентна.
"""
import logging

from datetime import timedelta

_logger = logging.getLogger(__name__)


def procent_kato_chislo(surov):
    """Дроб (0,51) или вече процент (51) → число от 0 до 100."""
    if not surov:
        return 0.0
    return surov * 100.0 if surov <= 1.0 else surov


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT v.employee_id, v.id, v.date_version, v.l10n_bg_disability_percent
        FROM hr_version v
        WHERE COALESCE(v.l10n_bg_disability_percent, 0) <> 0
          AND v.employee_id IS NOT NULL
        ORDER BY v.employee_id, v.date_version, v.id
    """)
    redove = cr.fetchall()
    if not redove:
        _logger.info("ТЕЛК: няма заварени проценти за пренасяне")
        return

    # служителите, които ВЕЧЕ имат решения — не се пипат втори път
    cr.execute("SELECT DISTINCT employee_id FROM l10n_bg_telk_decision")
    veche = {r[0] for r in cr.fetchall()}

    po_sluzhitel = {}
    for emp_id, _vid, data, procent in redove:
        if emp_id in veche:
            continue
        po_sluzhitel.setdefault(emp_id, []).append((data, procent))

    sazdadeni = 0
    for emp_id, zapisi in po_sluzhitel.items():
        # всяка ПРОМЯНА на процента е ново решение
        etapi = []
        for data, procent in zapisi:
            chislo = procent_kato_chislo(procent)
            if etapi and abs(etapi[-1][1] - chislo) < 0.005:
                continue
            etapi.append((data, chislo))

        for i, (ot, chislo) in enumerate(etapi):
            do = None
            if i + 1 < len(etapi):
                sledvashto = etapi[i + 1][0]
                if sledvashto and ot and sledvashto > ot:
                    do = sledvashto - timedelta(days=1)
            cr.execute("""
                INSERT INTO l10n_bg_telk_decision
                    (employee_id, company_id, number, issuing_body,
                     date_from, date_to, percent, active,
                     note, create_date, write_date)
                SELECT %s, e.company_id, %s, %s, %s, %s, %s, TRUE, %s,
                       NOW(), NOW()
                FROM hr_employee e WHERE e.id = %s
            """, (emp_id,
                  "(пренесено %s)" % (ot or "?"),
                  "(неизвестен)",
                  ot, do, int(round(chislo)),
                  "Пренесено от процента върху версията на договора при "
                  "въвеждането на историята на решенията. Номерът, органът и "
                  "датата на решението не са били налични — попълват се ръчно.",
                  emp_id))
            sazdadeni += cr.rowcount

    _logger.info("ТЕЛК: пренесени %s решения за %s служители "
                 "(%s вече имаха история)",
                 sazdadeni, len(po_sluzhitel), len(veche))
