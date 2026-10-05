# -*- coding: utf-8 -*-
"""Допълнително споразумение към трудовия договор (чл. 118-120 КТ).

Изнесено от `l10n_bg_hr_payroll` (18.0.18.11.0). Името на модела
`l10n_bg.hr.contract.amendment` и имената на всички заварени полета се ЗАПАЗВАТ
— таблицата и данните остават, `pre_init_hook` прехвърля собствеността.

Промени спрямо 18 (поведение от 19, адаптирано към `hr.contract`):

* `_inherits = {'hr.contract': 'contract_id'}` е МАХНАТО. ДС-то вече не пише
  основание и подписи върху договора — има собствени `legal_basis`,
  `signed_by_employee`, `signed_by_employer`. Миграцията на ТРЗ
  (18.0.19.0.0) копира заварените стойности от договора.
* `old_*` вече не са related+store към договора (дефект на 18: при
  активиране се презаписваха с новите стойности и историята изчезваше).
  Сега са снимка, взета при създаването (`_snapshot_old_values`).
* Активиране върху ДОГОВОРА на датата на влизане в сила
  (`cron_activate_due_amendments`); предсрочно — с изричен бутон и следа.
* Срочните ДС се връщат при изтичане от снимката; кронът е регистриран.
* Временно преместване по чл. 120 КТ — до 45 календарни дни в годината.
* Подпис след влизането в сила — предупреждение, не забрана.
* След активиране договореното е заключено.

🔑 В 18 НЯМА версии: всяка промяна се пише върху същия договор. Затова
активирането чака датата си (кронът), а връщането пипа САМО стойности, които
това ДС е поставило и които още стоят — иначе по-късна промяна би се загубила
тихо.
"""
import logging
from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

# Стойностите на типа работно време — същите като на договора (виж
# hr_contract.py). Дублирани нарочно: снимката е собствено поле, не related.
_WORKING_TIME_TYPES = [
    ('full_time', 'Full Time'),
    ('part_time', 'Part Time'),
    ('flexible', 'Flexible Hours'),
    ('summarized', 'Summarized Calculation')
]


def rec_za_proverka(records):
    """ДС-тата, които проверките по чл. 120 / чл. 267 съдят.

    🚨 В сила и изтеклите са ИСТОРИЯ — не се съдят наново. Причина: при
    инсталирането стореното `l10n_bg_assignment_days` се изчислява за
    заварените ДС, а Odoo вика ограниченията на изчисляемите полета
    (`models.py`, `_compute_field_value`). Заварено ДС с повече от 45 дни
    (в 18 таванът беше 12 месеца) иначе би свалило инсталацията. Броят им
    дни все пак влиза в сбора на НОВИТЕ.
    """
    return records.filtered(lambda r: r.state not in ('active', 'expired', 'cancel'))


class L10nBGHrContractAmendment(models.Model):
    """
    Допълнително споразумение към трудовия договор според КТ

    Според чл. 118 от КТ допълнителните споразумения се сключват:
    - При промяна на условията на труд
    - При временно преместване
    - При промяна на заплащането
    - При други съществени промени
    """
    _name = 'l10n_bg.hr.contract.amendment'
    _description = 'Bulgarian Contract Amendment'
    _order = 'date_signed desc, amendment_number desc'
    _rec_name = 'amendment_number'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _sequence_field = 'amendment_number'
    _sequence_date_field = "date_signed"
    _sequence_index = "contract_id"
    _check_company_domain = models.check_company_domain_parent_of

    # =========================================================================
    # ОСНОВНИ ПОЛЕТА
    # =========================================================================

    contract_id = fields.Many2one(
        'hr.contract',
        string='Main Contract',
        auto_join=True, index=True, ondelete="cascade", required=True,
        help='The main employment contract this amendment relates to'
    )

    amendment_number = fields.Char(
        string='Amendment Number',
        copy=False,
        default=False,
        readonly=True,
        index=True,
        help='Sequential number of amendment (e.g., 1/2024)'
    )

    # Стойностите на 18 се пазят; `leave_change` е добавено от 19.
    amendment_type = fields.Selection([
        ('wage_change', 'Wage Change'),
        ('position_change', 'Position Change'),
        ('workplace_change', 'Workplace Change'),
        ('working_time_change', 'Working Time Change'),
        ('temporary_assignment', 'Temporary Assignment'),
        ('leave_extension', 'Leave Extension'),
        ('contract_suspension', 'Contract Suspension'),
        ('contract_extension', 'Contract Extension'),
        ('additional_duties', 'Additional Duties'),
        ('other', 'Other Amendment'),
        ('leave_change', 'Leave Days Change'),
    ], string='Amendment Type',
        required=True,
        tracking=True,
        help='Type of contract amendment according to Bulgarian Labor Code')

    # =========================================================================
    # ДАТИ И ВАЛИДНОСТ
    # =========================================================================

    date_signed = fields.Date(
        string='Date Signed',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Date when the amendment was signed by both parties'
    )

    date_effective = fields.Date(
        string='Effective Date',
        required=True,
        tracking=True,
        help='Date when the amendment becomes effective'
    )

    date_end = fields.Date(
        string='End Date',
        help='End date for temporary amendments (e.g., temporary assignments)'
    )

    is_temporary = fields.Boolean(
        string='Temporary Amendment',
        default=False,
        help='Check if this amendment is temporary (e.g., temporary transfer)'
    )

    # Подписано след влизането в сила — ДОПУСТИМО (решение на Росен от 19):
    # отказът принуждаваше невярна дата на подписване. Само предупреждение.
    l10n_bg_signed_after_effective = fields.Boolean(
        string='Signed After Effective Date',
        compute='_compute_l10n_bg_signed_after_effective',
        help='The amendment was signed after the date it takes effect. This is '
             'allowed; the form only asks to check that the date is right.',
    )

    # Кой бутон има смисъл: докато датата не е настъпила, обикновеното
    # активиране отказва и на екрана стои „Активирай предсрочно“.
    l10n_bg_effective_in_future = fields.Boolean(
        string='Effective Date Not Reached',
        compute='_compute_l10n_bg_effective_in_future',
    )

    # =========================================================================
    # СЪДЪРЖАНИЕ НА СПОРАЗУМЕНИЕТО
    # =========================================================================

    subject = fields.Char(
        string='Subject',
        required=True,
        translate=True,
        help='Brief description of the amendment subject'
    )

    description = fields.Html(
        string='Amendment Details',
        translate=True,
        help='Detailed description of changes made by this amendment'
    )

    # 🔑 Собствено основание (в 18 през `_inherits` се пишеше
    # `hr.contract.l10n_bg_legal_basis` — едно за всички ДС на договора).
    legal_basis = fields.Text(
        string='Legal Basis',
        translate=True,
        help='Legal articles from Bulgarian Labor Code justifying this amendment',
    )

    # =========================================================================
    # ПРОМЕНИ — ЗАПЛАТА
    # =========================================================================

    # Снимка (не related): стойността на договора при създаването на ДС.
    old_wage = fields.Monetary(
        string='Previous Wage',
        currency_field='currency_id',
        readonly=True,
        help='Wage of the contract when the amendment was created'
    )

    new_wage = fields.Monetary(
        string='New Wage',
        currency_field='currency_id',
        help='Wage after this amendment'
    )

    wage_change_reason = fields.Text(
        string='Wage Change Reason',
        help='Reason for wage modification'
    )

    # =========================================================================
    # ПРОМЕНИ — ПОЗИЦИЯ (НКПД) И КИД
    # =========================================================================

    old_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='Previous NKPD Position',
        readonly=True,
        help='NKPD position of the contract when the amendment was created'
    )

    new_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='New NKPD Position',
        help='NKPD position after this amendment'
    )

    old_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='Previous Economic Activity',
        readonly=True,
        help='Economic activity of the contract when the amendment was created'
    )

    new_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='New Economic Activity',
        help='Economic activity after this amendment'
    )

    # =========================================================================
    # ПРОМЕНИ — РАБОТНО ВРЕМЕ
    # =========================================================================

    old_working_time_type = fields.Selection(
        _WORKING_TIME_TYPES,
        string='Previous Working Time Type',
        readonly=True,
    )

    new_working_time_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('flexible', 'Flexible Hours'),
        ('summarized', 'Summarized Calculation')
    ], string='New Working Time Type')

    old_daily_hours = fields.Float(
        string='Previous Daily Hours',
        readonly=True,
        help='Daily hours of the contract when the amendment was created'
    )

    new_daily_hours = fields.Float(string='New Daily Hours')

    # Седмичните часове на договора са в ТРЗ (`l10n_bg_weekly_hours`) —
    # снимката и прилагането ги пипат само ако полето съществува.
    old_weekly_hours = fields.Float(
        string='Previous Weekly Hours',
        readonly=True,
        help='Weekly hours of the contract when the amendment was created'
    )

    new_weekly_hours = fields.Float(string='New Weekly Hours')

    # =========================================================================
    # ПРОМЕНИ — РАБОТНО МЯСТО
    # =========================================================================

    # ⚠️ Текстовите полета остават за печат и за заварените ДС-та. Носителят е
    # записът `*_work_location_id` (от 19): текстът на договора е related към
    # адреса и запис в него не оцелява.
    old_work_location = fields.Char(
        string='Previous Work Location',
        readonly=True,
        help='Work location address of the contract when the amendment was created'
    )

    new_work_location = fields.Char(
        string='New Work Location',
        help='Legacy free text. The carrier is the New Work Location Record.'
    )

    old_work_location_id = fields.Many2one(
        'hr.work.location',
        string='Previous Work Location Record',
        readonly=True,
    )

    new_work_location_id = fields.Many2one(
        'hr.work.location',
        string='New Work Location Record',
        help="The work location record written on the contract when the "
             "amendment takes effect.",
    )

    # =========================================================================
    # ПРОМЕНИ — ОТПУСКИ (от 19)
    # =========================================================================

    old_leave_days = fields.Integer(
        string='Previous Leave Days', readonly=True,
        help='Basic annual leave of the contract when the amendment was created')
    new_leave_days = fields.Integer(
        string='New Leave Days',
        help='Basic annual leave days after this amendment')

    # =========================================================================
    # ВРЕМЕННО ПРЕМЕСТВАНЕ (ЧЛ. 120 КТ)
    # =========================================================================

    is_temporary_assignment = fields.Boolean(
        string='Temporary Assignment',
        help='Temporary assignment to other work under Art. 120 LC'
    )

    # ⚖️ Чл. 120, ал. 1 КТ: производствена необходимост И ПРЕСТОЙ, до 45
    # календарни дни в годината (при престой — докато трае). Стойностите на 18
    # се пазят; `idle_time` и `force_majeure` са добавени от 19.
    temporary_assignment_reason = fields.Selection([
        ('production_necessity', 'Production Necessity (Art. 120, para. 1 LC)'),
        ('employee_replacement', 'Employee Replacement'),
        ('urgent_work', 'Urgent Work'),
        ('natural_disaster', 'Natural Disaster'),
        ('other_emergency', 'Other Emergency'),
        ('idle_time', 'Idle Time (Art. 120, para. 1 LC)'),
        ('force_majeure', 'Compelling Reasons (Art. 120, para. 3 LC)'),
    ], string='Assignment Reason',
        help="The ground under Art. 120 LC. Idle time is the only one without "
             "a 45-day limit: the assignment lasts as long as the idle time "
             "does.")

    # 🔲 Заварено. Мярката на чл. 120 е в календарни дни, не в месеци —
    # проверката на 12-те месеца (дефект на 18) е заменена с 45-те дни.
    assignment_duration_months = fields.Integer(
        string='Assignment Duration (months, legacy)',
        readonly=True,
        help="Legacy. Art. 120 LC measures the assignment in calendar days; "
             "see Assignment Days.")

    l10n_bg_assignment_days = fields.Integer(
        string='Assignment Days',
        compute='_compute_l10n_bg_assignment_days', store=True,
        help="Calendar days of this assignment, derived from the effective and "
             "end dates. Art. 120, para. 1 LC caps them at 45 per calendar "
             "year, except during idle time.")

    # 🔲 Заварено. Носителят на мястото е „Ново работно място“ (запис).
    assignment_location = fields.Char(
        string='Assignment Location',
        help='Legacy free text. The carrier is the New Work Location Record.'
    )

    assignment_compensation = fields.Monetary(
        string='Assignment Compensation',
        currency_field='currency_id',
        help="Remuneration for the work actually performed during the "
             "assignment (Art. 267, para. 3 LC). It may not be lower than the "
             "gross remuneration for the main job. Left empty — the wage does "
             "not change.")

    # =========================================================================
    # СТАТУС, ОДОБРЕНИЕ, ПОДПИСИ
    # =========================================================================

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status',
        default='draft',
        required=True,
        tracking=True)

    approved_by_id = fields.Many2one(
        'res.users',
        string='Approved by',
        readonly=True,
        help='User who approved this amendment'
    )

    approved_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        help='Date when amendment was approved'
    )

    # 🔑 Собствени подписи (в 18 през `_inherits` се пишеха върху договора).
    signed_by_employee = fields.Boolean(
        string='Signed by Employee',
        help='Employee has signed the amendment',
    )
    signed_by_employer = fields.Boolean(
        string='Signed by Employer',
        help='Employer representative has signed the amendment',
    )

    # =========================================================================
    # ДОПЪЛНИТЕЛНИ ПОЛЕТА
    # =========================================================================

    currency_id = fields.Many2one(
        'res.currency',
        related='contract_id.currency_id',
        string='Currency',
        readonly=True
    )

    # store=True (от 19): правилото за фирмите и регистърът търсят по тях.
    company_id = fields.Many2one(
        'res.company',
        related='contract_id.company_id',
        string='Company',
        store=True,
        readonly=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        related='contract_id.employee_id',
        string='Employee',
        store=True,
        readonly=True
    )

    notes = fields.Text(
        string='Internal Notes',
        help='Internal notes about this amendment'
    )

    # =========================================================================
    # SEQUENCE MIXIN (без промяна от 18)
    # =========================================================================

    def _get_last_sequence_domain(self, relaxed=False):
        """Търсим последния номер само сред записи със същия договор."""
        self.ensure_one()
        where = "WHERE contract_id = %(cid)s"
        if relaxed:
            # при relaxed допускаме всяка година/месец на същия договор
            pass
        return where, {'cid': self.contract_id.id}

    def _get_starting_sequence(self):
        """
        Формат: {CONTRACT}/{YYYY}/0000
        Пример: CTR-0007/2024/0000  → първо споразумение става CTR-0007/2024/0001
        """
        self.ensure_one()
        prefix_contract = (self.contract_id.name or '').strip()
        year = fields.Date.today().year
        return f"{prefix_contract}/{year}/0000"

    # =========================================================================
    # COMPUTED FIELDS
    # =========================================================================

    @api.depends('amendment_number', 'amendment_type')
    def _compute_display_name(self):
        for record in self:
            if record.amendment_number and record.amendment_type:
                type_label = dict(record._fields['amendment_type'].selection)[record.amendment_type]
                record.display_name = f"{record.amendment_number} - {type_label}"
            else:
                record.display_name = record.amendment_number or _('New Amendment')

    wage_difference = fields.Monetary(
        string='Wage Difference',
        compute='_compute_wage_difference',
        currency_field='currency_id',
        help='Difference between new and old wage'
    )

    @api.depends('new_wage', 'old_wage')
    def _compute_wage_difference(self):
        for amendment in self:
            if amendment.new_wage and amendment.old_wage:
                amendment.wage_difference = amendment.new_wage - amendment.old_wage
            else:
                amendment.wage_difference = 0.0

    is_wage_increase = fields.Boolean(
        string='Wage Increase',
        compute='_compute_wage_increase',
        help='True if new wage is higher than old wage'
    )

    @api.depends('wage_difference')
    def _compute_wage_increase(self):
        for amendment in self:
            amendment.is_wage_increase = amendment.wage_difference > 0

    @api.depends('date_signed', 'date_effective')
    def _compute_l10n_bg_signed_after_effective(self):
        for rec in self:
            rec.l10n_bg_signed_after_effective = bool(
                rec.date_signed and rec.date_effective
                and rec.date_signed > rec.date_effective)

    @api.depends('date_effective')
    def _compute_l10n_bg_effective_in_future(self):
        dnes = fields.Date.context_today(self)
        for rec in self:
            rec.l10n_bg_effective_in_future = bool(
                rec.date_effective and rec.date_effective > dnes)

    @api.depends('date_effective', 'date_end', 'is_temporary_assignment')
    def _compute_l10n_bg_assignment_days(self):
        """Календарните дни на преместването — от датите, не от второ поле."""
        for rec in self:
            if (rec.is_temporary_assignment and rec.date_effective
                    and rec.date_end and rec.date_end >= rec.date_effective):
                rec.l10n_bg_assignment_days = (
                    rec.date_end - rec.date_effective).days + 1
            else:
                rec.l10n_bg_assignment_days = 0

    # =========================================================================
    # CONSTRAINTS AND VALIDATIONS
    # =========================================================================

    # Чл. 120, ал. 1 КТ — 45 календарни дни през една календарна година.
    _L10N_BG_ART120_DAYS_PER_YEAR = 45

    # Основанията, при които работодателят възлага БЕЗ съгласие (чл. 120) и
    # затова е обвързан с тавана. Останалите се уговарят по чл. 119, ал. 1.
    _L10N_BG_ART120_GROUNDS = (
        'production_necessity', 'idle_time', 'urgent_work',
        'natural_disaster', 'force_majeure',
    )

    @api.constrains('date_effective', 'date_end')
    def _check_effective_dates(self):
        for amendment in self:
            if amendment.date_end and amendment.date_effective:
                if amendment.date_effective >= amendment.date_end:
                    raise ValidationError(_("Amendment effective date must be before end date."))

    @api.constrains('amendment_number', 'contract_id')
    def _check_unique_amendment_number(self):
        for amendment in self:
            if amendment.amendment_number and amendment.contract_id:
                existing = self.search([
                    ('amendment_number', '=', amendment.amendment_number),
                    ('contract_id', '=', amendment.contract_id.id),
                    ('id', '!=', amendment.id)
                ])
                if existing:
                    raise ValidationError(_("Amendment number must be unique per contract."))

    @api.constrains('l10n_bg_assignment_days', 'temporary_assignment_reason',
                    'is_temporary_assignment', 'date_effective')
    def _check_assignment_duration(self):
        """Чл. 120, ал. 1 КТ — 45 КАЛЕНДАРНИ ДНИ за календарна година.

        Заменя проверката на 18 за 12 МЕСЕЦА (DEF-174 в 19). Таванът е за
        ГОДИНАТА — сумират се всички премествания по чл. 120 в нея. При престой
        таван няма. Споразумение по чл. 119 (съгласие) не се ограничава.
        """
        for rec in rec_za_proverka(self):
            if not rec.is_temporary_assignment or not rec.date_effective:
                continue
            if rec.temporary_assignment_reason not in self._L10N_BG_ART120_GROUNDS:
                continue
            if rec.temporary_assignment_reason == 'idle_time':
                continue
            if not rec.l10n_bg_assignment_days:
                continue
            godina = rec.date_effective.year
            drugi = self.search([
                ('id', '!=', rec.id or 0),
                ('employee_id', '=', rec.employee_id.id),
                ('is_temporary_assignment', '=', True),
                ('state', 'in', ('approved', 'active', 'expired')),
                ('temporary_assignment_reason', 'in',
                 [g for g in self._L10N_BG_ART120_GROUNDS if g != 'idle_time']),
                ('date_effective', '>=', date(godina, 1, 1)),
                ('date_effective', '<=', date(godina, 12, 31)),
            ])
            sbor = rec.l10n_bg_assignment_days + sum(
                drugi.mapped('l10n_bg_assignment_days'))
            if sbor > self._L10N_BG_ART120_DAYS_PER_YEAR:
                raise ValidationError(_(
                    "Temporary assignments for %(emp)s in %(year)s would total "
                    "%(total)d calendar days. Art. 120, para. 1 LC allows 45 "
                    "per calendar year, except during idle time.",
                    emp=rec.employee_id.display_name, year=godina, total=sbor))

    @api.constrains('new_work_location_id', 'old_work_location_id',
                    'is_temporary_assignment')
    def _check_assignment_settlement(self):
        """Чл. 120, ал. 1 КТ — „в същото населено място или местност“.

        Проверява се само когато и двете места носят населено място —
        липсващ адрес не е доказателство за нарушение.
        """
        for rec in rec_za_proverka(self):
            if not rec.is_temporary_assignment or not rec.new_work_location_id:
                continue
            if rec.temporary_assignment_reason not in self._L10N_BG_ART120_GROUNDS:
                continue
            staro = (rec.old_work_location_id.address_id.city or '').strip()
            novo = (rec.new_work_location_id.address_id.city or '').strip()
            if not staro or not novo or staro.casefold() == novo.casefold():
                continue
            raise ValidationError(_(
                "Art. 120, para. 1 LC allows a temporary assignment without "
                "the employee's consent only within the same settlement or "
                "locality. %(old)s and %(new)s are different settlements. Use "
                "a regular amendment with the employee's consent instead.",
                old=staro, new=novo))

    @api.constrains('assignment_compensation', 'old_wage',
                    'is_temporary_assignment')
    def _check_assignment_compensation(self):
        """Чл. 267, ал. 3 КТ — не по-малко от брутното за основната работа."""
        for rec in rec_za_proverka(self):
            if not rec.is_temporary_assignment or not rec.assignment_compensation:
                continue
            if not rec.old_wage:
                continue
            if float_compare(rec.assignment_compensation, rec.old_wage,
                             precision_digits=2) < 0:
                raise ValidationError(_(
                    "Assignment compensation %(new).2f is lower than the gross "
                    "remuneration for the main job %(old).2f. Art. 267, "
                    "para. 3 LC does not allow that.",
                    new=rec.assignment_compensation, old=rec.old_wage))

    # =========================================================================
    # ORM
    # =========================================================================

    # Полетата, които ОПИСВАТ договореното. След активирането са история —
    # смяната им би направила документа различен от записаното по договора.
    # ⚠️ Служебните (`state`, подписите, регистърът, НАП статусът) не са тук.
    _L10N_BG_LOCKED_AFTER_ACTIVATION = (
        'contract_id', 'amendment_type', 'date_signed', 'date_effective',
        'date_end', 'is_temporary', 'new_wage', 'new_position_id',
        'new_economic_activity_id', 'new_working_time_type', 'new_daily_hours',
        'new_weekly_hours', 'new_work_location', 'new_work_location_id',
        'new_leave_days', 'assignment_compensation',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Снимка на договора + номер от sequence.mixin.

        🔑 Снимката се взима ПРЕДИ записа: старите стойности са тези на
        договора при създаването на ДС-то. Подадена изрично стойност (импорт)
        не се презаписва.
        """
        Contract = self.env['hr.contract']
        for vals in vals_list:
            if vals.get('contract_id'):
                snimka = self._snapshot_old_values(
                    Contract.browse(vals['contract_id']))
                for field_name, value in snimka.items():
                    vals.setdefault(field_name, value)
        records = super().create(vals_list)
        # За всеки нов запис без номер – генерираме
        for rec in records.filtered(lambda r: not r.amendment_number):
            rec._set_next_sequence()
        return records

    def write(self, vals):
        zaklyucheni = set(vals) & set(self._L10N_BG_LOCKED_AFTER_ACTIVATION)
        if zaklyucheni:
            prilozheni = self.filtered(lambda r: r.state in ('active', 'expired'))
            if prilozheni:
                raise ValidationError(_(
                    "Amendment %(ref)s is already in force; %(fields)s can no "
                    "longer be changed. Editing it would make the signed "
                    "document differ from what was written on the contract. "
                    "Create a new amendment instead.",
                    ref=prilozheni[0].amendment_number or prilozheni[0].id,
                    fields=", ".join(sorted(zaklyucheni))))
        return super().write(vals)

    # =========================================================================
    # BUSINESS METHODS
    # =========================================================================

    def action_submit_for_approval(self):
        """Submit amendment for approval"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_("Only draft amendments can be submitted for approval."))

        self.state = 'to_approve'
        return True

    def action_approve(self):
        """Одобрение; попълва празните „предишни стойности“ (импорт/RPC)."""
        self.ensure_one()
        if self.state != 'to_approve':
            raise ValidationError(_("Only amendments pending approval can be approved."))

        vals = {
            'state': 'approved',
            'approved_by_id': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        }
        vals.update({
            field_name: value
            for field_name, value in self._snapshot_old_values(self.contract_id).items()
            if not self[field_name]
        })
        self.write(vals)
        return True

    def action_activate(self):
        """Активиране на настъпило ДС. Кронът минава оттук."""
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_("Only approved amendments can be activated."))
        dnes = fields.Date.context_today(self)
        if self.date_effective and self.date_effective > dnes:
            # 🔑 В 18 няма версии: запис днес важи и за дните преди датата на
            # влизане в сила. Затова предсрочното е отделно действие със следа.
            raise ValidationError(_(
                "Amendment %(ref)s takes effect on %(effective)s, which has "
                "not arrived yet. It will be activated automatically on that "
                "day. If it must take effect now, use 'Activate Early' — that "
                "action is recorded in the chatter.",
                ref=self.amendment_number or self.id,
                effective=self.date_effective))
        self._l10n_bg_do_activate()
        return True

    def action_activate_early(self):
        """Предсрочно активиране — минава, но оставя следа кой и кога."""
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_("Only approved amendments can be activated."))
        dnes = fields.Date.context_today(self)
        predsrochno = bool(self.date_effective and self.date_effective > dnes)
        self._l10n_bg_do_activate()
        if predsrochno:
            self.message_post(body=_(
                "Activated early on %(today)s, before the agreed effective "
                "date %(effective)s. The new terms are on the contract from "
                "today.",
                today=dnes, effective=self.date_effective))
        return True

    def _l10n_bg_do_activate(self):
        """Общото тяло: проверките и прилагането са на едно място."""
        self.ensure_one()
        self._l10n_bg_check_backdating()
        self._apply_contract_changes()
        self.state = 'active'

    def _l10n_bg_check_backdating(self):
        """Кука: отказ при връщане назад в ЗАТВОРЕН период.

        Този модул не зависи от ведомостта и не знае кое е затворено. Слоят с
        ведомостта може да override-не метода (виж ADR l10n-bg-ds-amendment/0006
        в 19).
        """
        return

    def action_cancel(self):
        """Cancel the amendment"""
        self.ensure_one()
        if self.state in ('active', 'expired'):
            raise ValidationError(_("Cannot cancel active or expired amendments."))

        self.state = 'cancel'
        return True

    # Състоянията, от които има връщане в чернова (DEF-175б в 19).
    _L10N_BG_STATES_WITH_A_WAY_BACK = ('draft', 'to_approve', 'approved',
                                       'cancel')

    def action_draft(self):
        """Връщане в чернова — изход от гардовете, без нов номер.

        „В сила“ и „изтекло“ НЕ се връщат: подписаният документ би се
        разминал със записаното по договора.
        """
        self.ensure_one()
        if self.state not in self._L10N_BG_STATES_WITH_A_WAY_BACK:
            raise ValidationError(_(
                "Amendment %(ref)s is %(state)s and cannot go back to draft. "
                "The signed document would differ from what was written on "
                "the contract. Create a new amendment instead.",
                ref=self.amendment_number or self.id,
                state=dict(self._fields['state']._description_selection(self.env)).get(self.state)))
        if self.state == 'draft':
            return True
        predi = self.state
        self.state = 'draft'
        self.message_post(body=_(
            "Reset to draft from %(state)s.",
            state=dict(self._fields['state']._description_selection(self.env)).get(predi)))
        return True

    # Типовете, чието съдържание е ТЕКСТ, а не величина по договора.
    _L10N_BG_TEXTUAL_TYPES = ('other', 'additional_duties',
                              'contract_suspension', 'leave_extension')

    def _l10n_bg_is_textual(self):
        """Договореното при този тип е описание, не стойност по договора."""
        self.ensure_one()
        return (self.amendment_type in self._L10N_BG_TEXTUAL_TYPES
                and bool(self.description))

    def _l10n_bg_contract_values(self):
        """Стойностите, които ДС-то пише върху договора."""
        self.ensure_one()
        contract = self.contract_id
        vals = {}
        if self.new_wage:
            vals['wage'] = self.new_wage
        if self.new_position_id:
            vals['l10n_bg_ncop_position_id'] = self.new_position_id.id
        if self.new_economic_activity_id:
            vals['l10n_bg_economic_activity_id'] = self.new_economic_activity_id.id
        if self.new_working_time_type:
            vals['l10n_bg_working_time_type'] = self.new_working_time_type
        if self.new_daily_hours:
            vals['l10n_bg_daily_hours'] = self.new_daily_hours
        if self.new_weekly_hours and 'l10n_bg_weekly_hours' in contract._fields:
            vals['l10n_bg_weekly_hours'] = self.new_weekly_hours
        if self.new_work_location_id:
            vals['work_location_id'] = self.new_work_location_id.id
        if self.new_leave_days:
            vals['l10n_bg_basic_leave_days'] = self.new_leave_days
        # ⚖️ Чл. 267, ал. 3 КТ — възнаграждението при преместване. Два
        # източника за една стойност се отказват явно.
        if self.is_temporary_assignment and self.assignment_compensation:
            if (self.new_wage and float_compare(
                    self.new_wage, self.assignment_compensation,
                    precision_digits=2) != 0):
                raise ValidationError(_(
                    "Amendment %(ref)s states both a new wage (%(wage).2f) and "
                    "an assignment compensation (%(comp).2f). They disagree — "
                    "fill in only one.",
                    ref=self.amendment_number or self.id,
                    wage=self.new_wage, comp=self.assignment_compensation))
            vals['wage'] = self.assignment_compensation
        # ⚖️ „Удължаване на срока“ пише УГОВОРЕНИЯ СРОК, не прекратяването.
        if self.amendment_type == 'contract_extension' and self.date_end:
            vals['l10n_bg_fixed_term_end'] = self.date_end
        return vals

    def _apply_contract_changes(self):
        """Прилага ДС-то върху договора (в 18 няма версии)."""
        self.ensure_one()
        if (self.is_temporary or self.is_temporary_assignment) and not self.date_end:
            raise ValidationError(_(
                "Amendment %(ref)s is temporary but has no end date. Without "
                "it the change would stay in force forever — the expiry cron "
                "looks for the end date.",
                ref=self.amendment_number or self.id))

        contract_values = self._l10n_bg_contract_values()

        if self.new_work_location and not self.new_work_location_id:
            # Текстът не е носител — казва се защо, вместо да се мълчи.
            _logger.warning(
                "ДС %s носи работно място само като текст (%r) — не се пише "
                "върху договора.", self.amendment_number, self.new_work_location)
            self.message_post(body=_(
                "The new work location is given only as text (%(text)s). It is "
                "not written on the contract — set the New Work Location "
                "Record instead.", text=self.new_work_location))

        if not contract_values and self._l10n_bg_is_textual():
            # Текстово споразумение: следа върху договора, без промяна.
            self.contract_id.message_post(
                body=_("Amendment %(ref)s in force from %(date)s: %(text)s",
                       ref=self.amendment_number or self.id,
                       date=self.date_effective,
                       text=self.description),
                subject=_("Contract Amendment"))
            return

        if not contract_values:
            # Явният отказ е по-евтин от документ „в сила“, който не мени нищо.
            raise ValidationError(_(
                "Amendment %(ref)s does not change anything on the contract. "
                "Fill in at least one new value — wage, NKPD position, economic "
                "activity, work location, working time or leave days — or "
                "cancel it. An amendment cannot take effect without a change.",
                ref=self.amendment_number or self.id))

        self.contract_id.write(contract_values)
        self.contract_id.message_post(
            body=_('Contract updated by amendment %s') % self.amendment_number,
            subject=_('Contract Amendment Applied')
        )

    @api.model
    def cron_activate_due_amendments(self):
        """Активира одобрените ДС, чиято дата на влизане в сила е настъпила.

        🚨 Редът е част от верността: активира се в реда, в който промените
        влизат в сила, иначе по-ранното ДС би презаписало по-късното.
        """
        dnes = fields.Date.today()
        due = self.search([
            ('state', '=', 'approved'),
            ('date_effective', '<=', dnes),
        ], order='date_effective asc, id asc')
        for amendment in due:
            # Грешка от едно ДС не спира партидата — остава „Одобрено“ с
            # бележка в чатъра.
            try:
                with self.env.cr.savepoint():
                    amendment.action_activate()
            except Exception as exc:  # noqa: BLE001 — логваме и продължаваме
                _logger.warning(
                    "Автоматичното активиране на ДС %s пропадна: %s",
                    amendment.amendment_number, exc)
                amendment.message_post(body=_(
                    "Automatic activation failed: %s. The amendment stays "
                    "approved and needs manual review.", exc))

    @api.model
    def cron_expire_temporary_amendments(self):
        """Изтичане на срочните ДС и връщане на предишните условия.

        🔑 Изтича в деня СЛЕД `date_end` (`<`, не `<=`): в 18 връщането пише
        върху същия договор, и в последния ден ДС-то още важи.
        """
        dnes = fields.Date.today()
        expired = self.search([
            ('state', '=', 'active'),
            ('is_temporary', '=', True),
            ('date_end', '<', dnes),
        ])
        for amendment in expired:
            amendment.state = 'expired'
            # Признакът е срочността (`is_temporary`), не типът.
            amendment._l10n_bg_revert_temporary()

    # Двойките (поле на договора, ново на ДС, старо на ДС), които връщането
    # пипа — същите носители като в 19.
    _L10N_BG_REVERTED = (
        ('wage', 'new_wage', 'old_wage'),
        ('l10n_bg_ncop_position_id', 'new_position_id', 'old_position_id'),
        ('work_location_id', 'new_work_location_id', 'old_work_location_id'),
        ('l10n_bg_economic_activity_id', 'new_economic_activity_id',
         'old_economic_activity_id'),
    )

    def _l10n_bg_revert_temporary(self):
        """Връща предишните условия от СНИМКАТА.

        🔑 Връща се само стойност, която ТОВА ДС е поставило и която още стои
        на договора. Ако друго ДС междувременно я е сменило, връщането би
        било тиха загуба на по-късна промяна (в 18 няма версии) — тогава не се
        пипа и причината влиза в чатъра.
        """
        self.ensure_one()
        contract = self.contract_id
        revert = {}
        propusnati = []
        for pole, novo, staro in self._L10N_BG_REVERTED:
            nova_st = self[novo]
            if pole == 'wage' and self.is_temporary_assignment \
                    and self.assignment_compensation and not nova_st:
                nova_st = self.assignment_compensation
            if not nova_st or not self[staro]:
                continue
            tekushta = contract[pole]
            if pole == 'wage':
                sashta = float_compare(tekushta, nova_st, precision_digits=2) == 0
                stara_st = self[staro]
            else:
                sashta = tekushta == nova_st
                stara_st = self[staro].id
            if sashta:
                revert[pole] = stara_st
            else:
                propusnati.append(contract._fields[pole]._description_string(self.env))
        if propusnati:
            self.message_post(body=_(
                "Not restored on expiry: %(fields)s. A later change is in force "
                "on the contract; restoring the previous value would silently "
                "undo it.", fields=", ".join(propusnati)))
        if not revert:
            return False
        contract.write(revert)
        contract.message_post(
            body=_('Temporary amendment %s expired; the previous terms are '
                   'restored.') % self.amendment_number,
            subject=_('Temporary Assignment Ended'),
        )
        return True

    def get_amendment_summary(self):
        """Какво мени това ДС — на човешки език, с етикети (от 19)."""
        self.ensure_one()
        changes = []

        def _etiket(ime_na_pole, stoynost):
            """Етикетът на списъчна стойност, преведен — не суровият код."""
            if not stoynost:
                return stoynost
            izbor = dict(self._fields[ime_na_pole]._description_selection(self.env))
            return izbor.get(stoynost, stoynost)

        if self.new_wage and self.old_wage != self.new_wage:
            changes.append(_('Wage: %(old).2f → %(new).2f',
                             old=self.old_wage, new=self.new_wage))
        if self.new_position_id and self.old_position_id != self.new_position_id:
            changes.append(_('NKPD Position: %(old)s → %(new)s',
                             old=self.old_position_id.name or '-',
                             new=self.new_position_id.name))
        if (self.new_work_location_id
                and self.old_work_location_id != self.new_work_location_id):
            changes.append(_('Work Location: %(old)s → %(new)s',
                             old=self.old_work_location_id.display_name or '-',
                             new=self.new_work_location_id.display_name))
        elif self.new_work_location and self.old_work_location != self.new_work_location:
            changes.append(_('Work Location: %(old)s → %(new)s',
                             old=self.old_work_location or '-',
                             new=self.new_work_location))
        if (self.new_working_time_type
                and self.old_working_time_type != self.new_working_time_type):
            changes.append(_('Working Time: %(old)s → %(new)s',
                             old=_etiket('old_working_time_type',
                                         self.old_working_time_type) or '-',
                             new=_etiket('new_working_time_type',
                                         self.new_working_time_type)))
        if self.new_leave_days and self.old_leave_days != self.new_leave_days:
            changes.append(_('Leave Days: %(old)d → %(new)d',
                             old=self.old_leave_days, new=self.new_leave_days))
        return '\n'.join(changes)

    # =========================================================================
    # СНИМКА И ONCHANGE
    # =========================================================================

    @api.model
    def _snapshot_old_values(self, contract):
        """Текущите стойности на договора като vals за old_* полетата."""
        if not contract:
            return {}
        vals = {
            'old_wage': contract.wage,
            'old_position_id': contract.l10n_bg_ncop_position_id.id,
            'old_economic_activity_id': contract.l10n_bg_economic_activity_id.id,
            'old_working_time_type': contract.l10n_bg_working_time_type,
            'old_daily_hours': contract.l10n_bg_daily_hours,
            'old_work_location': contract.work_location or False,
            'old_work_location_id': contract.work_location_id.id,
            'old_leave_days': contract.l10n_bg_basic_leave_days,
        }
        if 'l10n_bg_weekly_hours' in contract._fields:
            vals['old_weekly_hours'] = contract.l10n_bg_weekly_hours
        return vals

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        """Показва снимката още във формата."""
        if self.contract_id:
            for field_name, value in self._snapshot_old_values(self.contract_id).items():
                self[field_name] = value

    @api.onchange('amendment_type')
    def _onchange_amendment_type(self):
        """Set default values based on amendment type"""
        if self.amendment_type == 'temporary_assignment':
            self.is_temporary = True
            self.is_temporary_assignment = True
        else:
            self.is_temporary_assignment = False

    @api.onchange('is_temporary')
    def _onchange_is_temporary(self):
        """Clear end date if not temporary"""
        if not self.is_temporary and self.amendment_type != 'contract_extension':
            self.date_end = False
