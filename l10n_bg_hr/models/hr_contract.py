# -*- coding: utf-8 -*-
"""Трудовият договор по КТ — частта без ведомост.

Полетата под „ИЗНЕСЕНО ОТ ТРЗ“ са пренесени от `l10n_bg_hr_payroll`
(18.0.18.11.0, `models/hr_contract.py`) с ЕДНАКВИ имена и дефиниции: колоните
им в `hr_contract` вече съществуват и `pre_init_hook` прехвърля собствеността
на xmlid-ите им към този модул (виж `hooks.py`). Смяна на име или тип тук е
загуба на данни при миграция — не се прави без миграционен скрипт.

Полетата под „НОВО ОТ 19“ са пренесени от `l10n_bg_hr` 19.0.2.9.13, където
живеят на `hr.version`; тук са върху `hr.contract`, защото в 18 договорът е
носителят на правоотношението.
"""
import logging
from datetime import datetime, time, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # Колко дни ПРЕДИ срока да се предупреди — седем, колкото е срокът по
    # чл. 62, ал. 5 КТ за уведомлението до НАП.
    _L10N_BG_FIXED_TERM_LEAD_DAYS = 7

    # =========================================================================
    # ИЗНЕСЕНО ОТ ТРЗ — ИДЕНТИФИКАЦИЯ НА ДОГОВОРА
    # =========================================================================
    l10n_bg_contract_number = fields.Char(
        string="Labor Contract Number",
        copy=False,
        index=True,
        help="Unique labor contract number. Auto-filled from ir.sequence "
             "'l10n_bg.contract.number' on create if empty. Used in the "
             "ETZ XML <contractno> element (cell 11).",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-fill l10n_bg_contract_number from sequence if missing."""
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('l10n_bg_contract_number'):
                next_no = seq.next_by_code('l10n_bg.contract.number')
                if next_no:
                    vals['l10n_bg_contract_number'] = next_no
        return super().create(vals_list)

    # =========================================================================
    # ИЗНЕСЕНО ОТ ТРЗ — ЗАДЪЛЖИТЕЛНИ ПОЛЕТА ПО ЧЛ. 66 КТ
    # =========================================================================

    # 2. Място на работа (чл. 66, ал. 1, т. 1 КТ)
    work_location_id = fields.Many2one(
        related='employee_id.work_location_id',
        string='Work Location',
        readonly=False,
        store=True,
        help='Specific work location as required by Art. 66 of Labor Code',
    )

    work_location = fields.Char(
        string='Work Location Address',
        related='work_location_id.address_id.contact_address',
        readonly=True,
        store=True,
        help='Complete address of work location for contract display'
    )

    # 3. Наименование на длъжността и характер на работата (чл. 66, ал. 1, т. 2 КТ)
    l10n_bg_ncop_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='NKPD Position',
        help='Position according to NCOP-2011 classification as required by Art. 66 KT',
    )

    l10n_bg_job_description = fields.Text(
        string='Job Description',
        help='Character of work as required by Art. 66 of Labor Code'
    )

    # 4. Дата на сключването и началото на изпълнението (чл. 66, ал. 1, т. 3 КТ)
    l10n_bg_contract_date = fields.Date(
        string='Contract Conclusion Date',
        required=True,
        default=fields.Date.today,
        help='Date when contract was concluded as required by Art. 66 KT'
    )

    l10n_bg_termination_order_date = fields.Date(
        string='Termination Order Date',
        help='Date of the termination order (заповед за прекратяване); '
             'visible once the contract end date is set',
    )

    # 5. Времетраене на договора (чл. 66, ал. 1, т. 4 КТ)
    l10n_bg_contract_duration_type = fields.Selection(
        related='contract_type_id.l10n_bg_contract_duration_type',
        store=True,
        readonly=False,
    )

    l10n_bg_fixed_term_reason = fields.Text(
        string='Fixed Term Reason',
        help='Legal reason for fixed term contract according to Art. 68 KT'
    )

    # 6. Размер на основния и допълнителните отпуски (чл. 66, ал. 1, т. 5 КТ)
    l10n_bg_basic_leave_days = fields.Integer(
        string='Basic Annual Leave (days)',
        default=20,
        required=True,
        help='Basic paid annual leave in working days (min. 20 days per Labor Code)'
    )

    l10n_bg_extended_leave_days = fields.Integer(
        string='Extended Annual Leave (days)',
        default=0,
        help='Extended annual leave days if applicable'
    )

    l10n_bg_additional_leave_days = fields.Integer(
        string='Additional Leave Days',
        default=0,
        help='Additional leave days for specific conditions'
    )

    # 7. Срок за предизвестие (чл. 66, ал. 1, т. 6 КТ)
    l10n_bg_notice_period_days = fields.Integer(
        string='Notice Period (days)',
        default=30,
        required=True,
        help='Notice period for contract termination (30-90 days for indefinite contracts)'
    )

    # 9. Продължителност на работното време (чл. 66, ал. 1, т. 8 КТ)
    # ⚠️ Стойностите са тези на 18. В 19 има още „reduced“ и „shift“ — не се
    # добавят тук: ТРЗ 18 не ги познава и клонът за непълно време би ги
    # прочел като пълно.
    l10n_bg_working_time_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('flexible', 'Flexible Hours'),
        ('summarized', 'Summarized Calculation')
    ], string='Working Time Type',
        required=True,
        default='full_time',
        help='Type of working time as required by Art. 66 KT')

    l10n_bg_daily_hours = fields.Float(
        string='Daily Working Hours',
        default=8.0,
        help='Normal daily working hours'
    )

    # Икономическа дейност (КИД)
    l10n_bg_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='Economic Activity (NACE)',
        help='Economic activity according to Bulgarian KID classification for MOD calculation'
    )

    # ⚠️ Остава на договора (и в 18 там е): допълнителното споразумение вече
    # има СОБСТВЕНО основание — виж `legal_basis` в hr_contract_amendment.py.
    l10n_bg_legal_basis = fields.Text(
        string='Legal Basis',
        translate=True,
        help='Legal articles from Bulgarian Labor Code justifying this amendment'
    )

    # Свързани полета от НКПД позицията
    # ⚠️ Selection, НЕ Many2one като в 19 (решение на Росен, 05.10.2026).
    l10n_bg_qualification_group = fields.Selection(
        related='l10n_bg_ncop_position_id.qualification_group',
        string='Qualification Group',
        readonly=True,
        help='Qualification group from NKPD position'
    )

    l10n_bg_education_level = fields.Selection(
        related='l10n_bg_ncop_position_id.education_level',
        string='Required Education Level',
        readonly=True,
        help='Required education level for this position'
    )

    # Срок за изпитване
    l10n_bg_probation_period_days = fields.Integer(
        string='Probation Period (days)',
        default=0,
        help='Probation period in days (max 6 months according to KT)'
    )

    l10n_bg_signed_by_employee = fields.Boolean(
        string='Signed by Employee',
        help='Employee has signed the amendment'
    )

    l10n_bg_signed_by_employer = fields.Boolean(
        string='Signed by Employer',
        help='Employer representative has signed the amendment'
    )

    # Връзка към допълнителни споразумения
    l10n_bg_amendment_ids = fields.One2many(
        'l10n_bg.hr.contract.amendment',
        'contract_id',
        string='Contract Amendments',
        help='Additional agreements to the main contract according to Bulgarian Labor Code'
    )

    # =========================================================================
    # НОВО ОТ 19 — СРОЧНИЯТ ДОГОВОР: СРОКЪТ НЕ Е ПРЕКРАТЯВАНЕТО
    # =========================================================================
    # ⚖️ Ядреното `date_end` е ПРЕКРАТЯВАНЕТО. Срочният договор има УГОВОРЕН
    # СРОК, който може да изтече, без някой да прекрати; тогава чл. 69, ал. 1 КТ
    # действа сам. Затова срокът е собствено поле и не прекратява нищо.

    l10n_bg_fixed_term_end = fields.Date(
        string='Fixed Term End',
        tracking=True,
        help="The agreed end of a fixed-term contract (Art. 68 LC). This is "
             "NOT the termination date: the term may lapse without anyone "
             "terminating, and then Art. 69 LC converts the contract. Leave "
             "empty for open-ended contracts.",
    )

    # 🔑 В 18 договорът е правоотношението — нов вид след срока значи НОВ
    # договор, а него го решава човек. Затова полето само ПОДСКАЗВА (влиза в
    # предупреждението); кронът не ражда договор (за разлика от 19).
    l10n_bg_after_term_contract_type_id = fields.Many2one(
        'hr.contract.type',
        string='Contract After the Term',
        help="What the employment is expected to become once the fixed term "
             "lapses. It is only shown in the reminders — a new contract is "
             "never created automatically. Left empty — the reminder says the "
             "contract is to be terminated on the term date.",
    )

    # =========================================================================
    # НОВО ОТ 19 — СБОРНИ ПОЛЕТА
    # =========================================================================
    l10n_bg_total_leave_days = fields.Integer(
        string='Total Annual Leave Days',
        compute='_compute_l10n_bg_total_leave_days',
        store=True,
        help='Total annual leave days (basic + extended + additional)',
    )

    l10n_bg_amendment_count = fields.Integer(
        string='Amendment Count',
        compute='_compute_l10n_bg_amendment_count',
    )

    @api.depends('l10n_bg_basic_leave_days', 'l10n_bg_extended_leave_days',
                 'l10n_bg_additional_leave_days')
    def _compute_l10n_bg_total_leave_days(self):
        # В 18 отпускът има ТРИ части (в 19 — две), затова и удълженият влиза.
        for contract in self:
            contract.l10n_bg_total_leave_days = (
                contract.l10n_bg_basic_leave_days
                + contract.l10n_bg_extended_leave_days
                + contract.l10n_bg_additional_leave_days)

    @api.depends('l10n_bg_amendment_ids')
    def _compute_l10n_bg_amendment_count(self):
        for contract in self:
            contract.l10n_bg_amendment_count = len(contract.l10n_bg_amendment_ids)

    # =========================================================================
    # ИЗНЕСЕНО ОТ ТРЗ — ПРОВЕРКИ (стъпват само на изнесените полета)
    # =========================================================================

    @api.constrains('l10n_bg_basic_leave_days')
    def _check_minimum_leave(self):
        for contract in self:
            if contract.l10n_bg_basic_leave_days < 20:
                raise ValidationError(
                    _("Basic annual leave cannot be less than 20 working days according to Labor Code."))

    @api.constrains('l10n_bg_notice_period_days', 'l10n_bg_contract_duration_type')
    def _check_notice_period(self):
        for contract in self:
            if contract.l10n_bg_contract_duration_type == 'indefinite':
                if contract.l10n_bg_notice_period_days < 30 or contract.l10n_bg_notice_period_days > 90:
                    raise ValidationError(_("Notice period for indefinite contracts must be between 30 and 90 days."))

    @api.constrains('l10n_bg_probation_period_days')
    def _check_probation_period(self):
        for contract in self:
            if contract.l10n_bg_probation_period_days > 180:  # 6 months
                raise ValidationError(_("Probation period cannot exceed 180 days (6 months)."))

    @api.constrains('l10n_bg_contract_date', 'date_start')
    def _check_contract_dates(self):
        for contract in self:
            if contract.l10n_bg_contract_date > contract.date_start:
                raise ValidationError(_("Contract conclusion date cannot be after the start date."))

    @api.constrains('contract_type_id', 'l10n_bg_fixed_term_end')
    def _l10n_bg_check_fixed_term_end(self):
        """DEF-173б (от 19) — срочен договор без срок е запис, който кронът не вижда.

        ⚖️ Само при ``fixed_term``: „до завършване на определена работа“ и
        заместването нямат календарна дата по своята природа.

        🔑 Проверката виси на ``contract_type_id`` (стореният източник), не на
        related-а ``l10n_bg_contract_duration_type``. Пали само при ЗАПИС на
        тези полета — заварените договори не се проверяват при инсталацията.
        """
        for contract in self:
            vid = contract.contract_type_id
            if not vid or vid.l10n_bg_contract_duration_type != 'fixed_term':
                continue
            if contract.sudo().l10n_bg_fixed_term_end:
                continue
            raise ValidationError(_(
                "Contract type %(type)s is a fixed-term ground (Art. 68, "
                "para. 1 LC), so the agreed end of the term is required. "
                "Without it the contract is invisible to the expiry reminders, "
                "and Art. 69 LC can never be applied.",
                type=vid.display_name))

    # =========================================================================
    # ИЗНЕСЕНО ОТ ТРЗ — ONCHANGE
    # =========================================================================

    @api.onchange('job_id')
    def on_change_job_id(self):
        # В 18 НКПД идва от длъжността; КИД — също, ако длъжността го носи
        # (полето на длъжността е ново, от 19).
        for record in self:
            if record.job_id:
                record.l10n_bg_ncop_position_id = record.job_id.l10n_bg_ncop_position_id
                if record.job_id.l10n_bg_economic_activity_id:
                    record.l10n_bg_economic_activity_id = (
                        record.job_id.l10n_bg_economic_activity_id)

    @api.onchange('l10n_bg_contract_duration_type')
    def _onchange_contract_duration_type(self):
        """Set appropriate defaults based on contract type"""
        if self.l10n_bg_contract_duration_type == 'indefinite':
            self.l10n_bg_notice_period_days = 30
        else:
            self.l10n_bg_notice_period_days = 0

    @api.onchange('contract_type_id')
    def _onchange_contract_type_id(self):
        if (self.l10n_bg_contract_duration_type
            and self.l10n_bg_contract_duration_type == self.contract_type_id.l10n_bg_contract_duration_type):
            self.l10n_bg_contract_duration_type = self.contract_type_id.l10n_bg_contract_duration_type

    # =========================================================================
    # НОВО ОТ 19 — КРОНОВЕ ПО СРОЧНИЯ ДОГОВОР
    # =========================================================================

    def _l10n_bg_fixed_term_deadline(self):
        """Срокът плюс петте работни дни на чл. 69, ал. 1 КТ.

        🔑 РАБОТНИ, не календарни — през календара на договора. Петте дни
        текат СЛЕД срока и НЕ го включват (DEF-173 в 19).
        """
        self.ensure_one()
        srok = self.sudo().l10n_bg_fixed_term_end
        if not srok:
            return False
        calendar = (self.resource_calendar_id
                    or self.company_id.resource_calendar_id)
        nachalo = datetime.combine(srok + timedelta(days=1), time.min)
        if not calendar:
            # Без календар не могат да се броят работни дни — по-честно е да
            # се падне на календарни, отколкото да се пропусне срокът.
            _logger.warning(
                "Договор %s няма календар — петте работни дни по чл. 69 се "
                "броят като календарни.", self.id)
            return srok + timedelta(days=5)
        kray = calendar.plan_days(5, nachalo, compute_leaves=True)
        return kray.date() if kray else srok + timedelta(days=5)

    def _l10n_bg_after_term_outcome(self):
        """Какво следва след срока — текст за предупрежденията."""
        self.ensure_one()
        sledva = self.sudo().l10n_bg_after_term_contract_type_id
        if sledva:
            return _("it is expected to continue as %(ground)s — a new "
                     "contract has to be concluded for that",
                     ground=sledva.display_name)
        return _("it is to be TERMINATED on that date — no ground is set for "
                 "what follows")

    @api.model
    def cron_l10n_bg_notify_expiring_fixed_terms(self):
        """Предупреждава ПРЕДИ срока — заради уведомлението до НАП.

        ⚖️ Прекратяването по чл. 62, ал. 5 КТ се уведомява в НАП, а
        уведомлението иска подготовка. Стигне ли се до срока неподготвено,
        чл. 69 действа сам.

        Дедупликация: една дейност за един срок (по резюмето), тъй че
        ежедневният крон не трупа повторения.
        """
        dnes = fields.Date.today()
        prag = dnes + timedelta(days=self._L10N_BG_FIXED_TERM_LEAD_DAYS)
        dogovori = self.sudo().search([
            ('state', 'in', ('draft', 'open')),
            ('l10n_bg_fixed_term_end', '!=', False),
            ('l10n_bg_fixed_term_end', '<=', prag),
            ('l10n_bg_fixed_term_end', '>=', dnes),
            ('date_end', '=', False),
            ('l10n_bg_contract_duration_type', '!=', 'indefinite'),
        ])
        broi = 0
        for contract in dogovori:
            srok = contract.l10n_bg_fixed_term_end
            rezyume = _("Fixed term of %(employee)s ends on %(date)s",
                        employee=contract.employee_id.name or contract.name,
                        date=srok)
            if not contract._l10n_bg_schedule_once(rezyume, srok):
                continue
            contract.message_post(body=_(
                "Fixed term ends on %(date)s: %(outcome)s. File the NRA "
                "notification under Art. 62(5) LC in time — once five working "
                "days pass with the employee still at work and no written "
                "objection, Art. 69 LC converts the contract by law and the "
                "choice is no longer yours.",
                date=srok, outcome=contract._l10n_bg_after_term_outcome()))
            broi += 1
        if broi:
            _logger.info("Срочни договори с изтичащ срок до %s: %s", prag, broi)
        return broi

    @api.model
    def cron_l10n_bg_close_overdue_fixed_terms(self):
        """Последната мрежа: срокът е минал и петте работни дни също.

        🚨 Разлика с 19 (решение на Росен, 05.10.2026): в 18 договорът Е
        правоотношението, а нов договор е ново правоотношение. Затова кронът НЕ
        прекратява и НЕ ражда договор — само МАРКИРА (червено `kanban_state`,
        както ядреното `update_state` прави за изтичащите договори), оставя
        дейност на отговорния и следа в чатъра. Решава човек.
        """
        dnes = fields.Date.today()
        dogovori = self.sudo().search([
            ('state', '=', 'open'),
            ('l10n_bg_fixed_term_end', '!=', False),
            ('l10n_bg_fixed_term_end', '<', dnes),
            ('date_end', '=', False),
            ('l10n_bg_contract_duration_type', '!=', 'indefinite'),
        ])
        markirani = self.browse()
        for contract in dogovori:
            deadline = contract._l10n_bg_fixed_term_deadline()
            if not deadline or dnes <= deadline:
                # Прозорецът на чл. 69 още тече — човекът има думата.
                continue
            srok = contract.l10n_bg_fixed_term_end
            rezyume = _("Fixed term of %(employee)s lapsed on %(date)s",
                        employee=contract.employee_id.name or contract.name,
                        date=srok)
            if not contract._l10n_bg_schedule_once(rezyume, dnes):
                continue
            contract.message_post(body=_(
                "The fixed term lapsed on %(date)s and five working days have "
                "passed with no end date on the contract. Under Art. 69(1) LC "
                "the contract may already be converted into an open-ended one. "
                "Expected outcome: %(outcome)s. Nothing was changed "
                "automatically — terminate the contract or conclude the new "
                "one.",
                date=srok, outcome=contract._l10n_bg_after_term_outcome()))
            markirani |= contract
        if markirani:
            markirani.write({'kanban_state': 'blocked'})
            _logger.info("Срочни договори след прозореца на чл. 69: %s "
                         "маркирани", len(markirani))
        return len(markirani)

    def _l10n_bg_schedule_once(self, rezyume, srok):
        """Дейност „за свършване“ на отговорния — веднъж за едно резюме.

        Връща True, ако е създадена нова дейност. Приключената дейност изчезва
        от `mail.activity`; тогава кронът я ражда пак — нарочно, срокът още
        стои.
        """
        self.ensure_one()
        Activity = self.env['mail.activity'].sudo()
        if Activity.search_count([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('summary', '=', rezyume),
        ]):
            return False
        admin = self.env.ref('base.user_admin', raise_if_not_found=False)
        otgovornik = self.hr_responsible_id or admin or self.env.user
        self.with_context(mail_activity_quick_update=True).activity_schedule(
            'mail.mail_activity_data_todo', srok,
            summary=rezyume, user_id=otgovornik.id)
        return True
