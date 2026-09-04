# -*- coding: utf-8 -*-

import logging
from datetime import datetime, time, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class HrVersion(models.Model):
    _inherit = 'hr.version'

    # =========================================================================
    # CONTRACT IDENTIFICATION (BG convention — separate from base `name`)
    # =========================================================================
    # Base `name` stays free text (Odoo standard). BG-specific labor contract
    # number is stored separately so it can be used in ETZ XML <contractno>
    # (cell 11) and legacy ERP integrations.

    l10n_bg_contract_number = fields.Char(
        string="Labor Contract Number",
        copy=False,
        index=True,
        help="Unique labor contract number. Auto-filled from ir.sequence "
             "'l10n_bg.contract.number' on create if empty. Used in the "
             "ETZ XML <contractno> element (cell 11).",
    )

    work_location = fields.Char(
        string='Work Location Address',
        related='work_location_id.address_id.contact_address',
        readonly=True,
        store=True,
        help='Complete address of work location for contract display'
    )

    # Contract type specific to Bulgaria
    l10n_bg_contract_duration_type = fields.Selection(
        related='contract_type_id.l10n_bg_contract_duration_type',
        string='BG Contract Duration Type',
        store=True,
        readonly=True
    )
    l10n_bg_uic = fields.Char(
        related='company_id.l10n_bg_uic',
        string='Company UIC',
        readonly=True,
        store=True
    )

    # Employee identification
    l10n_bg_egn = fields.Char(
        related='employee_id.identification_id',
        string='EGN',
        readonly=True,
        store=True
    )

    # =========================================================================
    # СРОЧНИЯТ ДОГОВОР — СРОКЪТ НЕ Е ПРЕКРАТЯВАНЕТО
    # =========================================================================
    # ⚖️ Днес двете се събират в едно поле. Ядреният `contract_date_end` е
    # ПРЕКРАТЯВАНЕТО — денят, в който правоотношението свършва. Срочният
    # договор обаче има УГОВОРЕН СРОК, който може да изтече, без някой да
    # прекрати; тогава чл. 69, ал. 1 КТ действа сам: продължи ли работникът
    # пет или повече работни дни след срока без писмено възражение от
    # работодателя, договорът се смята за променен в БЕЗСРОЧЕН.
    #
    # Затова срокът е СОБСТВЕНО поле. То не прекратява нищо — то е датата, до
    # която важи основанието по чл. 68 КТ.

    # Колко дни ПРЕДИ срока да се предупреди. Седем, колкото е срокът по
    # чл. 62, ал. 5 КТ за уведомлението до НАП — така ТРЗ-то има целия
    # законов прозорец, а не остатъка от него.
    _L10N_BG_FIXED_TERM_LEAD_DAYS = 7

    l10n_bg_fixed_term_end = fields.Date(
        string='Fixed Term End',
        groups='hr.group_hr_user',
        help="The agreed end of a fixed-term contract (Art. 68 LC). This is "
             "NOT the termination date: the term may lapse without anyone "
             "terminating, and then Art. 69 LC converts the contract. Leave "
             "empty for open-ended contracts.",
    )

    l10n_bg_after_term_contract_type_id = fields.Many2one(
        'hr.contract.type',
        string='Contract After the Term',
        groups='hr.group_hr_user',
        help="What the employment becomes once the fixed term lapses. Filled "
             "in — a new version is born on the next day under this ground. "
             "Left EMPTY — the contract is terminated on the term date.",
    )

    def _l10n_bg_fixed_term_deadline(self):
        """Срокът плюс петте работни дни на чл. 69, ал. 1 КТ.

        🔑 РАБОТНИ, не календарни — затова минава през календара на версията,
        а не през `timedelta(5)`. Празници и почивни дни местят границата.
        """
        self.ensure_one()
        if not self.l10n_bg_fixed_term_end:
            return False
        calendar = (self.resource_calendar_id
                    or self.company_id.resource_calendar_id)
        # 🚨 DEF-173 — поправка на собствен off-by-one (02.09.2026, мерено от
        # Пламена). Чл. 69, ал. 1 КТ: „продължи да работи СЛЕД изтичане на
        # уговорения срок 5 или повече работни дни". Петте дни текат СЛЕД
        # срока и НЕ го включват.
        #
        # Първата версия броеше от самата дата на срока, тъй че когато тя е
        # работен ден, тя ставаше ден номер едно. Следствието е законов
        # прозорец, скъсен с един работен ден: кронът можеше да прекрати или
        # превърне договор, докато работникът още има думата — точно това,
        # което докстрингът на самия крон твърди, че избягва.
        nachalo = datetime.combine(
            self.l10n_bg_fixed_term_end + timedelta(days=1), time.min)
        if not calendar:
            # Без календар не може да се броят работни дни. По-честно е да се
            # падне на календарни, отколкото да се пропусне срокът мълчаливо.
            _logger.warning(
                "Версия %s няма календар — петте работни дни по чл. 69 се "
                "броят като календарни.", self.id)
            return self.l10n_bg_fixed_term_end + timedelta(days=5)
        return calendar.plan_days(5, nachalo, compute_leaves=True).date()

    # =========================================================================
    # PROFESSIONAL QUALIFICATIONS
    # =========================================================================

    l10n_bg_qualification_group = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='Qualification Group (NKPD)',
        compute='_compute_l10n_bg_qualification_group',
        store=True,
        readonly=False,
        help='Professional qualification according to NKPD nomenclature. '
             'Auto-populated from the selected job position '
             '(hr.job.l10n_bg_ncop_position_id) but can be manually '
             'overridden.'
    )

    l10n_bg_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='Economic Activity (KID)',
        compute='_compute_l10n_bg_economic_activity_id',
        store=True,
        readonly=False,
        default=False,
        help='Economic activity according to KID 2008. Auto-populated '
             'from the selected job or company but can be overridden.'
    )

    @api.depends('job_id', 'job_id.l10n_bg_ncop_position_id')
    def _compute_l10n_bg_qualification_group(self):
        """Always mirrors the job's NKPD when job changes."""
        for version in self:
            if version.job_id and version.job_id.l10n_bg_ncop_position_id:
                version.l10n_bg_qualification_group = (
                    version.job_id.l10n_bg_ncop_position_id
                )

    @api.depends('job_id', 'job_id.l10n_bg_economic_activity_id', 'company_id')
    def _compute_l10n_bg_economic_activity_id(self):
        """Mirrors the job's КИД, falls back to company default."""
        for version in self:
            job_kid = (version.job_id.l10n_bg_economic_activity_id
                       if version.job_id else False)
            if job_kid:
                version.l10n_bg_economic_activity_id = job_kid
            elif (not version.l10n_bg_economic_activity_id
                  and version.company_id
                  and version.company_id.l10n_bg_economic_activity_id):
                version.l10n_bg_economic_activity_id = (
                    version.company_id.l10n_bg_economic_activity_id
                )

    def action_refresh_nkpd_kid(self):
        """Refresh НКПД and КИД from current job position."""
        for version in self:
            job = version.job_id
            if not job:
                continue
            vals = {}
            if job.l10n_bg_ncop_position_id:
                vals['l10n_bg_qualification_group'] = job.l10n_bg_ncop_position_id.id
            if job.l10n_bg_economic_activity_id:
                vals['l10n_bg_economic_activity_id'] = job.l10n_bg_economic_activity_id.id
            if vals:
                version.write(vals)

    @api.onchange('job_id')
    def _onchange_job_id_propagate_nkpd(self):
        """Instant UI feedback when user changes job in the form."""
        if self.job_id and self.job_id.l10n_bg_ncop_position_id:
            self.l10n_bg_qualification_group = (
                self.job_id.l10n_bg_ncop_position_id
            )
        if self.job_id and self.job_id.l10n_bg_economic_activity_id:
            self.l10n_bg_economic_activity_id = (
                self.job_id.l10n_bg_economic_activity_id
            )

    l10n_bg_economic_activity_code = fields.Char(
        string='Economic Activity Code',
        related='l10n_bg_economic_activity_id.code',
        store=True,
        readonly=True,
        help='Economic activity code according to KID 2008'
    )

    l10n_bg_workplace_code = fields.Char(
        string='Workplace Code (EKATTE)',
        help='Workplace location code according to EKATTE'
    )

    # =========================================================================
    # WORKING TIME
    # =========================================================================

    # 🔑 ЕДНА селекция за целия стек. Дотук базовият модул носеше '1'..'6', а
    # ведомостта ПРЕЗАПИСВАШЕ полето с несъвместими стойности — тъй че версии,
    # записани преди инсталирането на ведомостта, оставаха с код, който новата
    # селекция не признава, и клонът за непълно работно време не палеше НИКОГА.
    #
    # ⚖️ „Намалено" (чл. 137 КТ) и „непълно" (чл. 138 КТ) са РАЗЛИЧНИ и цената
    # е парична: при намалено работникът запазва възнаграждението и правата по
    # осигурителното законодателство, тоест МОД НЕ се проратира; при непълно
    # МОД е пропорционален на времето. Затова има отделна клетка за намалено.
    l10n_bg_working_time_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('reduced', 'Reduced Working Time (Art. 137 LC)'),
        ('part_time', 'Part Time (Art. 138 LC)'),
        ('flexible', 'Flexible Hours'),
        ('shift', 'Shift Work'),
        ('summarized', 'Summarized Calculation'),
    ], string='Working Time Type',
        default='full_time',
        help='Type of working time organization. Reduced working time keeps '
             'full pay and full social security rights; part-time is '
             'proportional.')

    l10n_bg_daily_hours = fields.Float(
        string='Daily Hours',
        compute='_compute_daily_hours',
        store=True,
        help='Standard daily working hours'
    )

    # =========================================================================
    # LEAVE DAYS
    # =========================================================================

    l10n_bg_basic_leave_days = fields.Integer(
        string='Basic Annual Leave Days',
        default=20,
        help='Minimum annual leave days according to Bulgarian Labor Code'
    )

    l10n_bg_additional_leave_days = fields.Integer(
        string='Additional Leave Days',
        default=0,
        help='Additional annual leave days beyond basic entitlement'
    )

    l10n_bg_total_leave_days = fields.Integer(
        string='Total Annual Leave Days',
        compute='_compute_total_leave_days',
        store=True,
        help='Total annual leave days (basic + additional)'
    )

    # =========================================================================
    # CONTRACT AMENDMENTS
    # =========================================================================

    l10n_bg_amendment_ids = fields.One2many(
        'l10n_bg.hr.version.amendment',
        'version_id',
        string='Contract Amendments',
    )

    l10n_bg_amendment_count = fields.Integer(
        string='Amendment Count',
        compute='_compute_amendment_count',
    )

    @api.depends('l10n_bg_amendment_ids')
    def _compute_amendment_count(self):
        for version in self:
            version.l10n_bg_amendment_count = len(version.l10n_bg_amendment_ids)

    # =========================================================================
    # COMPUTED METHODS
    # =========================================================================

    @api.depends('resource_calendar_id.hours_per_day')
    def _compute_daily_hours(self):
        """Calculate daily working hours"""
        for version in self:
            if version.resource_calendar_id:
                version.l10n_bg_daily_hours = version.resource_calendar_id.hours_per_day
            else:
                version.l10n_bg_daily_hours = 8.0

    @api.depends('l10n_bg_basic_leave_days', 'l10n_bg_additional_leave_days')
    def _compute_total_leave_days(self):
        """Calculate total annual leave days"""
        for version in self:
            version.l10n_bg_total_leave_days = (
                    version.l10n_bg_basic_leave_days + version.l10n_bg_additional_leave_days
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

    def action_open_version(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.version',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'current',
        }

    # =========================================================================
    # КРОНОВЕ ПО СРОЧНИЯ ДОГОВОР
    # =========================================================================

    @api.model
    def cron_l10n_bg_notify_expiring_fixed_terms(self):
        """Предупреждава ПРЕДИ срока — заради уведомлението до НАП.

        ⚖️ Това е същинската работа. Прекратяването по чл. 62, ал. 5 КТ се
        уведомява в НАП, а уведомлението иска подготовка; стигне ли се до
        срока неподготвено, изборът вече не е свободен — чл. 69 действа сам.
        Затова кронът долу е ПОСЛЕДНАТА мрежа, а този е нормалният път.
        """
        dnes = fields.Date.today()
        prag = dnes + timedelta(days=self._L10N_BG_FIXED_TERM_LEAD_DAYS)
        versii = self.search([
            ('l10n_bg_fixed_term_end', '!=', False),
            ('l10n_bg_fixed_term_end', '<=', prag),
            ('l10n_bg_fixed_term_end', '>=', dnes),
            ('contract_date_end', '=', False),
            ('l10n_bg_contract_duration_type', '!=', 'indefinite'),
        ])
        for version in versii:
            if version.l10n_bg_after_term_contract_type_id:
                iztod = _(
                    "it will continue as %(ground)s from the next day",
                    ground=version.l10n_bg_after_term_contract_type_id.display_name)
            else:
                iztod = _("it will be TERMINATED on that date — no ground is "
                          "set for what follows")
            version.message_post(body=_(
                "Fixed term ends on %(date)s: %(outcome)s. File the NRA "
                "notification under Art. 62(5) LC in time — once five working "
                "days pass with the employee still at work and no written "
                "objection, Art. 69 LC converts the contract by law and the "
                "choice is no longer yours.",
                date=version.l10n_bg_fixed_term_end, outcome=iztod))
        if versii:
            _logger.info(
                "Срочни договори с изтичащ срок до %s: %s", prag, len(versii))
        return len(versii)

    @api.model
    def cron_l10n_bg_close_overdue_fixed_terms(self):
        """Последната мрежа: срокът е минал и петте работни дни също.

        🚨 Кронът пише по ТРУДОВИ ПРАВООТНОШЕНИЯ без човек в стаята. Затова:
        · пали се само след петте работни дни по чл. 69, ал. 1 — дотогава
          човекът още може да действа и мрежата не пречи;
        · пропуска всяка версия с попълнено `contract_date_end` — прекратено е,
          няма какво да се довършва;
        · оставя следа в чатъра за ВСЯКО свое действие.

        ⚖️ Празното „договор след срока" значи ПРЕКРАТЯВАНЕ на датата на срока
        (решение на Росен, 01.09.2026). Попълненото ражда нова версия със
        своето основание.

        ⚖️ Чл. 69, ал. 2 КТ изключва от превръщането договорите по чл. 68,
        ал. 1, т. 2 — „до завършване на определена работа". Те се разпознават
        машинно по `l10n_bg_contract_duration_type == 'specific_work'`, тъй
        че за тях петте дни не са законов прозорец, а само отсрочка: срокът им
        свършва, когато работата е завършена, и автоматично превръщане няма.
        Изчакването се пази еднакво за всички по решение на Росен („винаги е
        5 дни"), защото по-рано действие би отнело на човека времето да
        реагира.

        🔑 Новата версия започва от `срок + 1`, не от самата дата на срока —
        конвенцията на модула (изходът от срочно ДС също ражда версия от
        `date_end + 1`). Две версии върху ЕДИН ден биха дали припокриващи се
        подпериоди в т. 14/15 на Д1.
        """
        dnes = fields.Date.today()
        versii = self.search([
            ('l10n_bg_fixed_term_end', '!=', False),
            ('l10n_bg_fixed_term_end', '<', dnes),
            ('contract_date_end', '=', False),
            ('l10n_bg_contract_duration_type', '!=', 'indefinite'),
        ])
        pipnati = 0
        for version in versii:
            deadline = version._l10n_bg_fixed_term_deadline()
            if not deadline or dnes <= deadline:
                # Прозорецът на чл. 69 още тече — човекът има думата.
                continue
            srok = version.l10n_bg_fixed_term_end
            version.contract_date_end = srok
            osnovanie = version.l10n_bg_after_term_contract_type_id
            if osnovanie:
                nova = version.copy({
                    'date_version': srok + timedelta(days=1),
                    'contract_date_start': srok + timedelta(days=1),
                    'contract_date_end': False,
                    'contract_type_id': osnovanie.id,
                    'l10n_bg_fixed_term_end': False,
                    'l10n_bg_after_term_contract_type_id': False,
                })
                version.message_post(body=_(
                    "The fixed term lapsed on %(date)s and five working days "
                    "passed. The contract is closed on that date and version "
                    "%(new)s continues from the next day under %(ground)s.",
                    date=srok, new=nova.display_name,
                    ground=osnovanie.display_name))
                _logger.info(
                    "Срочен договор на версия %s затворен на %s; нова версия "
                    "%s с основание %s.", version.id, srok, nova.id,
                    osnovanie.display_name)
            else:
                version.message_post(body=_(
                    "The fixed term lapsed on %(date)s and five working days "
                    "passed with no ground set for what follows. The contract "
                    "is terminated on the term date.", date=srok))
                _logger.info(
                    "Срочен договор на версия %s прекратен на %s (няма "
                    "договор след срока).", version.id, srok)
            pipnati += 1
        return pipnati
