"""Видът работно време: от '1'..'6' към семантичните стойности.

Базовият модул носеше '1'..'6', а ведомостта ПРЕЗАПИСВАШЕ полето с
`full_time/part_time/flexible/summarized`. Версии, записани преди
инсталирането на ведомостта, оставаха с код, който новата селекция не
признава — и клонът за непълно работно време (`== 'part_time'`) не палеше
НИКОГА за тях, тоест прората на МОД мълчеше.

⚖️ Мапингът е нормативен, не технически: „намалено" (чл. 137 КТ) и „непълно"
(чл. 138) са различни неща. При намалено работникът запазва възнаграждението и
осигурителните права ⇒ МОД НЕ се проратира; при непълно е пропорционален.
Затова '2' отива в собствена клетка `reduced`, а не в `part_time`.

🚨 SQL, а не ORM: старите стойности вече не са в селекцията и ORM би отказал да
ги прочете.
"""
import logging

_logger = logging.getLogger(__name__)

MAPING = {
    "1": "full_time",
    "2": "reduced",      # чл. 137 — пълно възнаграждение, пълни осиг. права
    "3": "part_time",    # чл. 138 — пропорционален МОД
    "4": "flexible",
    "5": "shift",
    "6": "summarized",
}


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        SELECT column_name FROM information_schema.columns
         WHERE table_name = 'hr_version'
           AND column_name = 'l10n_bg_working_time_type'
    """)
    if not cr.fetchone():
        return

    obshto = 0
    for staro, novo in MAPING.items():
        cr.execute("""
            UPDATE hr_version
               SET l10n_bg_working_time_type = %s
             WHERE l10n_bg_working_time_type = %s
        """, (novo, staro))
        if cr.rowcount:
            _logger.info(
                "[l10n_bg_hr] вид работно време %r → %r: %d версии",
                staro, novo, cr.rowcount)
            obshto += cr.rowcount

    # Каквото не е нито стара, нито нова стойност, се показва — не се гади.
    cr.execute("""
        SELECT DISTINCT l10n_bg_working_time_type
          FROM hr_version
         WHERE l10n_bg_working_time_type IS NOT NULL
           AND l10n_bg_working_time_type NOT IN (
               'full_time', 'reduced', 'part_time', 'flexible',
               'shift', 'summarized')
    """)
    chuzhdi = [r[0] for r in cr.fetchall()]
    if chuzhdi:
        _logger.warning(
            "[l10n_bg_hr] непознати стойности за вид работно време, НЕ са "
            "пипани: %s. Прората на МОД няма да пали за тях — прегледай ги.",
            ", ".join(chuzhdi))

    _logger.info("[l10n_bg_hr] пренесени %d версии; непознати %d",
                 obshto, len(chuzhdi))
