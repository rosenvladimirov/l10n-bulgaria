# -*- coding: utf-8 -*-
"""Прехвърляне на собствеността от `l10n_bg_hr_payroll` към `l10n_bg_hr`.

Образец: `l10n_bg_civil_base/hooks.py` (nra.income.code).

🔑 Защо `pre_init_hook`, а не pre-migrate: хукът се изпълнява ПРЕДИ този
модул да зареди моделите и данните си, при ПЪРВАТА му инсталация. Така при
заварена база с ТРЗ xmlid-ите вече са на `l10n_bg_hr`, когато той ги зарежда —
записите се ОБНОВЯВАТ (res_id се пази), вместо да се раждат нови, а
почистването на ТРЗ при неговия ъпгрейд (`ir.model.data._process_end`) не
вижда нищо „изоставено“ за триене.

🚨 Трите капана, заради които списъкът е ИЗРИЧЕН (не LIKE):
1. Видовете договори (21 записа `l10n_bg_0XX`) — ако останат на ТРЗ, ТРЗ ги
   изтрива при ъпгрейда си, а `hr.contract.contract_type_id` пада на NULL
   (114 договора на Теолино губят вида си ТИХО).
2. `seq_l10n_bg_contract_number` е noupdate — ако не се прехвърли, тук се
   ражда ВТОРА последователност със същия код и номерацията тръгва от 00001.
3. Поле, което ТРЗ спре да дефинира и което никой друг не дефинира, се трие
   заедно с колоната (DROP COLUMN). Списъкът по-долу съвпада ТОЧНО с полетата,
   които този модул дефинира и които ТРЗ досега притежаваше — проверява се
   статично с `tools/check_xmlid_transfer.py`.

⚖️ Какво НЕ е в списъка и защо е безопасно:
· служебните и наследените от миксини полета на ДС (`id`, `create_uid`,
  `message_ids`, `activity_ids`, `sequence_prefix`, …) — този модул става
  „оригинален“ за модела и Odoo им създава свои xmlid-и при зареждането
  (ir_model.py, `_reflect_fields`: `module == model._original_module`);
  старите на ТРЗ после се махат САМО като xmlid, защото записът има друг
  (ir_model.py, `_process_end`: „if the record has other associated xids, only
  remove the xid“);
· делегираните през `_inherits` полета на договора върху ДС (`wage`,
  `name`, …) — `_inherits` се маха, полетата им НЕ са съхранени в таблицата
  на ДС (няма колони), и изчезването им при ъпгрейда на ТРЗ е желано.

Odoo 18: хукът получава `env` (не `cr`).
"""
import logging

_logger = logging.getLogger(__name__)

SOURCE_MODULE = 'l10n_bg_hr_payroll'
TARGET_MODULE = 'l10n_bg_hr'

# --- ir.model ----------------------------------------------------------------
MODEL_XMLIDS = (
    'model_l10n_bg_hr_contract_amendment',
)

# --- ir.model.fields: полетата на договора, изнесени от ТРЗ ------------------
HR_CONTRACT_FIELDS = (
    'l10n_bg_contract_number',
    'work_location_id',
    'work_location',
    'l10n_bg_ncop_position_id',
    'l10n_bg_job_description',
    'l10n_bg_contract_date',
    'l10n_bg_termination_order_date',
    'l10n_bg_contract_duration_type',
    'l10n_bg_fixed_term_reason',
    'l10n_bg_basic_leave_days',
    'l10n_bg_extended_leave_days',
    'l10n_bg_additional_leave_days',
    'l10n_bg_notice_period_days',
    'l10n_bg_working_time_type',
    'l10n_bg_daily_hours',
    'l10n_bg_economic_activity_id',
    'l10n_bg_legal_basis',
    'l10n_bg_qualification_group',
    'l10n_bg_education_level',
    'l10n_bg_probation_period_days',
    'l10n_bg_signed_by_employee',
    'l10n_bg_signed_by_employer',
    'l10n_bg_amendment_ids',
)

HR_EMPLOYEE_FIELDS = (
    'l10n_bg_ncop_position_id',
    'l10n_bg_qualification_group',
    'l10n_bg_economic_activity_id',
)

HR_CONTRACT_TYPE_FIELDS = (
    'l10n_bg_contract_duration_type',
)

# --- ir.model.fields: собствените (декларирани) полета на ДС ----------------
AMENDMENT_FIELDS = (
    'contract_id',
    'amendment_number',
    'amendment_type',
    'date_signed',
    'date_effective',
    'date_end',
    'is_temporary',
    'subject',
    'description',
    'old_wage',
    'new_wage',
    'wage_change_reason',
    'old_position_id',
    'new_position_id',
    'old_economic_activity_id',
    'new_economic_activity_id',
    'old_working_time_type',
    'new_working_time_type',
    'old_daily_hours',
    'new_daily_hours',
    'old_weekly_hours',
    'new_weekly_hours',
    'old_work_location',
    'new_work_location',
    'is_temporary_assignment',
    'temporary_assignment_reason',
    'assignment_duration_months',
    'assignment_location',
    'assignment_compensation',
    'state',
    'approved_by_id',
    'approved_date',
    'currency_id',
    'company_id',
    'employee_id',
    'notes',
    'wage_difference',
    'is_wage_increase',
)

# --- ir.model.fields.selection: стойностите на литералните Selection-и ------
SELECTIONS = {
    ('hr_contract', 'l10n_bg_working_time_type'): (
        'full_time', 'part_time', 'flexible', 'summarized'),
    ('hr_contract_type', 'l10n_bg_contract_duration_type'): (
        'indefinite', 'fixed_term', 'specific_work', 'replacement'),
    ('l10n_bg_hr_contract_amendment', 'amendment_type'): (
        'wage_change', 'position_change', 'workplace_change',
        'working_time_change', 'temporary_assignment', 'leave_extension',
        'contract_suspension', 'contract_extension', 'additional_duties',
        'other'),
    ('l10n_bg_hr_contract_amendment', 'new_working_time_type'): (
        'full_time', 'part_time', 'flexible', 'summarized'),
    ('l10n_bg_hr_contract_amendment', 'temporary_assignment_reason'): (
        'production_necessity', 'employee_replacement', 'urgent_work',
        'natural_disaster', 'other_emergency'),
    ('l10n_bg_hr_contract_amendment', 'state'): (
        'draft', 'to_approve', 'approved', 'active', 'expired', 'cancel'),
}

# --- данни: записите от data/ и security/ на ТРЗ, които се местят -----------
DATA_XMLIDS = (
    # hr.contract.type — 21 вида договори (капан 1)
    'l10n_bg_001', 'l10n_bg_002', 'l10n_bg_003', 'l10n_bg_004',
    'l10n_bg_005', 'l10n_bg_006', 'l10n_bg_007', 'l10n_bg_008',
    'l10n_bg_009', 'l10n_bg_010', 'l10n_bg_011', 'l10n_bg_012',
    'l10n_bg_013', 'l10n_bg_014', 'l10n_bg_015', 'l10n_bg_016',
    'l10n_bg_017', 'l10n_bg_018', 'l10n_bg_019', 'l10n_bg_020',
    'l10n_bg_021',
    # ir.sequence — noupdate (капан 2)
    'seq_l10n_bg_contract_number',
    # ir.model.access + ir.rule на ДС
    'access_l10n_bg_hr_contract_amendment_user',
    'access_l10n_bg_hr_contract_amendment_hr_user',
    'access_l10n_bg_hr_contract_amendment_hr_manager',
    'access_l10n_bg_hr_contract_amendment_hr_officer',
    'rule_l10n_bg_hr_contract_amendment_multi_company',
    # ir.ui.view / ir.actions.act_window / ir.ui.menu на ДС
    'view_l10n_bg_hr_contract_amendment_list',
    'view_l10n_bg_hr_contract_amendment_form',
    'view_l10n_bg_hr_contract_amendment_search',
    'view_l10n_bg_hr_contract_amendment_kanban',
    'view_l10n_bg_hr_contract_amendment_calendar',
    'view_l10n_bg_hr_contract_amendment_pivot',
    'action_l10n_bg_hr_contract_amendment',
    'action_l10n_bg_hr_contract_amendment_from_contract',
    'menu_l10n_bg_hr_contract_amendment',
    'view_hr_contract_form_amendment_button',
    'view_hr_contract_form_amendment_tab',
    # ir.ui.view на вида договор
    'hr_contract_type_view_form',
)


def _field_xmlid(model_table, field_name):
    """Името на xmlid-а на поле — като `odoo.addons.base.models.ir_model.field_xmlid`."""
    return 'field_%s__%s' % (model_table, field_name)


def _selection_xmlid(model_table, field_name, value):
    """Като `selection_xmlid` в ядрото (стойността с `.`/` ` → `_`)."""
    xmlid = 'selection__%s__%s__%s' % (model_table, field_name, value)
    return xmlid.replace('.', '_').replace(' ', '_').lower()


def transfer_xmlids():
    """Пълният ИЗРИЧЕН списък от имена (без модул), които се прехвърлят."""
    names = list(MODEL_XMLIDS)
    names += [_field_xmlid('hr_contract', f) for f in HR_CONTRACT_FIELDS]
    names += [_field_xmlid('hr_employee', f) for f in HR_EMPLOYEE_FIELDS]
    names += [_field_xmlid('hr_contract_type', f) for f in HR_CONTRACT_TYPE_FIELDS]
    names += [_field_xmlid('l10n_bg_hr_contract_amendment', f)
              for f in AMENDMENT_FIELDS]
    for (table, field_name), values in SELECTIONS.items():
        names += [_selection_xmlid(table, field_name, v) for v in values]
    names += list(DATA_XMLIDS)
    assert len(names) == len(set(names)), "повторено име в списъка"
    return names


def pre_init_hook(env):
    """Прехвърля xmlid-ите от ТРЗ, ако ТРЗ е инсталиран (иначе — нищо)."""
    cr = env.cr
    cr.execute("""
        SELECT state FROM ir_module_module WHERE name = %s
    """, (SOURCE_MODULE,))
    row = cr.fetchone()
    if not row or row[0] not in ('installed', 'to upgrade', 'to remove'):
        _logger.info("%s: %s не е инсталиран — няма какво да се прехвърля",
                     TARGET_MODULE, SOURCE_MODULE)
        return

    names = transfer_xmlids()

    # Гард: при вече съществуващо същото име под този модул UPDATE-ът би
    # нарушил unique(module, name). На нормален път това не се случва (модулът
    # се инсталира за първи път) — ако се случи, спираме, вместо да гадаем.
    cr.execute("""
        SELECT name FROM ir_model_data
         WHERE module = %s AND name = ANY(%s)
    """, (TARGET_MODULE, names))
    sblasaci = [r[0] for r in cr.fetchall()]
    if sblasaci:
        raise RuntimeError(
            "%s: xmlid-ите вече съществуват под %s: %s" % (
                TARGET_MODULE, TARGET_MODULE, ", ".join(sorted(sblasaci))))

    cr.execute("""
        UPDATE ir_model_data
           SET module = %s
         WHERE module = %s
           AND name = ANY(%s)
        RETURNING name, model
    """, (TARGET_MODULE, SOURCE_MODULE, names))
    prehvarleni = cr.fetchall()
    po_model = {}
    for _name, model in prehvarleni:
        po_model[model] = po_model.get(model, 0) + 1
    lipsvashti = sorted(set(names) - {n for n, _m in prehvarleni})
    _logger.info(
        "%s: прехвърлени %s от %s xmlid-а от %s (%s)",
        TARGET_MODULE, len(prehvarleni), len(names), SOURCE_MODULE,
        ", ".join("%s: %s" % kv for kv in sorted(po_model.items())))
    if lipsvashti:
        # Не е грешка сама по себе си (напр. заварена база отпреди някое поле),
        # но се вижда в лога, за да се свери с базата.
        _logger.warning(
            "%s: %s xmlid-а от списъка ги няма под %s: %s",
            TARGET_MODULE, len(lipsvashti), SOURCE_MODULE,
            ", ".join(lipsvashti))

    # 🚨 Видовете договори — КРИТИЧНИ (капан 1): ако някой от тях го няма под
    # ТРЗ, а в базата съществува под друго име, тук ще се роди дубликат.
    # Логва се изрично, за да се хване на копието.
    cr.execute("""
        SELECT count(*) FROM ir_model_data
         WHERE module = %s AND model = 'hr.contract.type'
    """, (TARGET_MODULE,))
    _logger.info("%s: видове договори под модула след прехвърлянето: %s",
                 TARGET_MODULE, cr.fetchone()[0])


def post_init_hook(env):
    """База БЕЗ ТРЗ (напр. с l10n_bg_hr_payroll_oca): поправя датата на сключване.

    `l10n_bg_contract_date` е задължително с подразбиране „днес“. Когато
    колоната се ражда тук (ТРЗ го няма и тя не е съществувала), Odoo попълва
    заварените договори с ДАТАТА НА ИНСТАЛАЦИЯТА — по-късна от началото им, а
    `_check_contract_dates` отказва всеки следващ запис по такъв договор.
    Затова за заварените се взима началото на договора.

    ⚠️ При база с ТРЗ колоната е заварена и данните не се пипат.
    """
    cr = env.cr
    cr.execute("SELECT state FROM ir_module_module WHERE name = %s",
               (SOURCE_MODULE,))
    row = cr.fetchone()
    if row and row[0] in ('installed', 'to upgrade', 'to remove'):
        return
    cr.execute("""
        UPDATE hr_contract
           SET l10n_bg_contract_date = date_start
         WHERE date_start IS NOT NULL
           AND l10n_bg_contract_date > date_start
           AND create_date < (now() AT TIME ZONE 'UTC') - interval '1 minute'
    """)
    if cr.rowcount:
        _logger.info("%s: дата на сключване = начало на договора за %s "
                     "заварени договора", TARGET_MODULE, cr.rowcount)
