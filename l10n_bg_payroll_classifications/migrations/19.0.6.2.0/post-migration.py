"""Пренася заварените МОД стойности в датирани редове — БЕЗ да мръдне число.

Плоските колони ``mod_*`` носят по ЕДНА стойност на дейност, валидна „винаги".
Датирането ги замества, но пренасянето трябва да е неутрално: всяко изчисление
отпреди миграцията да дава същия резултат след нея, за ВСЯКА дата.

🔑 Затова началната дата е ``SEED_DATE`` (много ранна), а не датата на самите
стойности. Заварените суми СА за януари 2026, но плоското поле ги прилага и за
2025, и за 2024 — това е днешното поведение и миграцията НЕ го поправя, а го
запазва. Поправянето назад е отделен въпрос: то мени приключени периоди.

  преди:  фиш от 03.2025 → mod_manager = X
  след:   фиш от 03.2025 → ред с date_from 2000-01-01 → X        (същото)
  после:  фиш от 09.2026 → ред с date_from 2026-08-01 → Y        (новото)

⚠️ Плоските колони НЕ се трият. Те остават резерва за дейност, създадена
по-късно без датирани редове, и следа откъде е дошъл сеедът.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

MODULE = "l10n_bg_payroll_classifications"

# Ранна дата: „толкова назад, колкото плоското поле реално важеше".
SEED_DATE = "2000-01-01"

GROUPS = (
    "military", "manager", "specialist", "technician",
    "clerk", "service", "skilled", "operator", "elementary",
)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Activity = env["bg.hr.payroll.economic.activity"].sudo()
    Value = env["bg.hr.payroll.mod.value"].sudo()

    if Value.search_count([("date_from", "=", SEED_DATE)]):
        _logger.info(
            "[%s] сеедът вече е минал — нищо за пренасяне.", MODULE)
        return

    vals = []
    activities = Activity.with_context(active_test=False).search([])
    for activity in activities:
        for group in GROUPS:
            amount = getattr(activity, "mod_%s" % group, 0.0) or 0.0
            # Нулата в плоското поле значи „наследи нагоре", НЕ „няма праг".
            # Пренасянето ѝ като ред би СПРЯЛО обхождането и би сменило
            # поведението — точно това миграцията не бива да прави.
            if not amount:
                continue
            vals.append({
                "activity_id": activity.id,
                "qualification_group": group,
                "date_from": SEED_DATE,
                "amount": amount,
                "source": "seed: flat mod_%s column" % group,
            })
    if vals:
        Value.create(vals)

    with_rows = len({v["activity_id"] for v in vals})
    _logger.info(
        "[%s] пренесени %d стойности от %d дейности (от общо %d). Дейностите "
        "без нито една ненулева колона остават без редове — за тях обхождането "
        "нагоре работи както преди.",
        MODULE, len(vals), with_rows, len(activities))

    # Контрола: сверяваме НА СЛУЧАЕН ПРИНЦИП, че четенето дава същото.
    # Проверява се самият метод, не препис на формулата.
    checked = drift = 0
    for activity in activities[:40]:
        for group in GROUPS:
            before = getattr(activity, "mod_%s" % group, 0.0) or 0.0
            if not before:
                continue
            after = activity.get_effective_mod(group, "2026-01-15")
            checked += 1
            if abs(after - before) > 0.005:
                drift += 1
                _logger.warning(
                    "[%s] РАЗМИНАВАНЕ: %s / %s — плоско %.2f, датирано %.2f",
                    MODULE, activity.code, group, before, after)
    _logger.info(
        "[%s] сверени %d двойки чрез самия get_effective_mod: %d разминавания.",
        MODULE, checked, drift)
