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

🚨 Източникът може изобщо да го няма. `l10n_bg_disability_percent` е махнат
от кода заедно с този рефакторинг, а бази, които никога не са го носили,
стигат дотук без колоната. Затова тя се проверява, преди да се чете — инак
първото четене сваля целия ъпгрейд с „column does not exist".
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
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'hr_version'
           AND column_name = 'l10n_bg_disability_percent'
    """)
    if not cr.fetchone():
        _logger.info(
            "ТЕЛК: `l10n_bg_disability_percent` го няма в тази база — "
            "няма заварени проценти за пренасяне")
        return

    cr.execute("""
        SELECT v.employee_id, v.id, v.date_version, v.l10n_bg_disability_percent
        FROM hr_version v
        WHERE COALESCE(v.l10n_bg_disability_percent, 0) <> 0
          AND v.employee_id IS NOT NULL
          AND v.date_version IS NOT NULL
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
    otpadnali = 0
    for emp_id, zapisi in po_sluzhitel.items():
        # всяка ПРОМЯНА на процента е ново решение
        etapi = []
        for data, procent in zapisi:
            chislo = int(round(procent_kato_chislo(procent)))
            # Гардът на модела иска 1..100. Стойност, която се закръгля под
            # единица, не е решение — минава за нула и записът пада на
            # първото отваряне на формата.
            if not 1 <= chislo <= 100:
                otpadnali += 1
                continue
            if etapi and etapi[-1][1] == chislo:
                continue
            etapi.append((data, chislo))

        # Номерът е част от unique(employee_id, number). Две версии в един и
        # същи ден с различен процент дават два етапа с еднаква дата — без
        # брояча вторият INSERT сваля целия ъпгрейд.
        vidyani = {}
        for i, (ot, chislo) in enumerate(etapi):
            do = None
            if i + 1 < len(etapi):
                sledvashto = etapi[i + 1][0]
                if sledvashto and ot and sledvashto > ot:
                    do = sledvashto - timedelta(days=1)
            nomer = "(пренесено %s)" % (ot or "?")
            vidyani[nomer] = vidyani.get(nomer, 0) + 1
            if vidyani[nomer] > 1:
                nomer = "%s #%s" % (nomer, vidyani[nomer])
            cr.execute("""
                INSERT INTO l10n_bg_telk_decision
                    (employee_id, company_id, number, issuing_body,
                     date_from, date_to, percent, active,
                     note, create_date, write_date)
                SELECT %s, e.company_id, %s, %s, %s, %s, %s, TRUE, %s,
                       NOW(), NOW()
                FROM hr_employee e WHERE e.id = %s
            """, (emp_id,
                  nomer,
                  "(неизвестен)",
                  ot, do, chislo,
                  "Пренесено от процента върху версията на договора при "
                  "въвеждането на историята на решенията. Номерът, органът и "
                  "датата на решението не са били налични — попълват се ръчно.",
                  emp_id))
            sazdadeni += cr.rowcount

    if otpadnali:
        _logger.warning(
            "ТЕЛК: %s записа отпаднаха — процентът им се закръгля извън "
            "1..100. Прегледай ги: стойността е или повредена, или в единица, "
            "която пренасянето не разпознава.", otpadnali)

    _logger.info("ТЕЛК: пренесени %s решения за %s служители "
                 "(%s вече имаха история)",
                 sazdadeni, len(po_sluzhitel), len(veche))
