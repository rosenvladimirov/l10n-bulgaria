# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class L10nBGHrVersionAmendment(models.Model):
    """Допълнително споразумение към трудовия договор (чл. 118 КТ)"""
    _name = 'l10n_bg.hr.version.amendment'
    _description = 'Contract Amendment'
    _order = 'date_signed desc, id desc'
    _rec_name = 'amendment_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_domain = models.check_company_domain_parent_of

    # =========================================================================
    # ОСНОВНИ ПОЛЕТА
    # =========================================================================

    amendment_number = fields.Char(
        string='Amendment Number',
        copy=False,
        default=lambda self: _('New'),
        readonly=True,
        index=True,
    )

    version_id = fields.Many2one(
        'hr.version',
        string='Contract Version',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
        domain="[('employee_id', '!=', False)]",
    )

    # 🔑 `version_id` е версията, КОЯТО ДС-то изменя — изходната. Версията,
    # която активирането РАЖДА, дотук не се записваше никъде. Затова всеки
    # консуматор (НАП експорт, ЕТЗ уведомление, бланка) четеше изходната и
    # описваше състоянието ПРЕДИ споразумението, включително заплатата, която
    # ДС-то е записало вярно.
    # Ново поле, а не пренасочване на `version_id`: то храни
    # `l10n_bg_amendment_ids`, `_compute_last_amendment` и историята — местенето
    # му би поискало миграция на всичко това.
    applied_version_id = fields.Many2one(
        'hr.version',
        string='Applied Version',
        readonly=True,
        copy=False,
        index=True,
        help="The contract version this amendment produced when activated. "
             "Reports and declarations must read this one, not the version "
             "the amendment started from.",
    )

    employee_id = fields.Many2one(
        related='version_id.employee_id',
        string='Employee',
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        related='version_id.company_id',
        string='Company',
        store=True,
        readonly=True,
    )

    amendment_type = fields.Selection([
        ('wage_change', 'Wage Change'),
        ('position_change', 'Position Change'),
        ('workplace_change', 'Workplace Change'),
        ('working_time_change', 'Working Time Change'),
        ('leave_change', 'Leave Days Change'),
        ('temporary_assignment', 'Temporary Assignment'),
        ('contract_extension', 'Contract Extension'),
        ('additional_duties', 'Additional Duties'),
        ('other', 'Other Amendment'),
    ], string='Amendment Type',
        required=True,
        tracking=True,
    )

    # =========================================================================
    # ДАТИ И ВАЛИДНОСТ
    # =========================================================================

    date_signed = fields.Date(
        string='Date Signed',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )

    date_effective = fields.Date(
        string='Effective Date',
        required=True,
        tracking=True,
    )

    date_end = fields.Date(
        string='End Date',
    )

    is_temporary = fields.Boolean(
        string='Temporary Amendment',
        default=False,
    )

    # Показва кой бутон има смисъл: докато датата не е настъпила, обикновеното
    # активиране отказва и на екрана стои „Активирай предсрочно".
    l10n_bg_effective_in_future = fields.Boolean(
        string='Effective Date Not Reached',
        compute='_compute_l10n_bg_effective_in_future',
    )

    # =========================================================================
    # СЪДЪРЖАНИЕ
    # =========================================================================

    subject = fields.Char(
        string='Subject',
        required=True,
        translate=True,
    )

    description = fields.Html(
        string='Amendment Details',
        translate=True,
    )

    legal_basis = fields.Text(
        string='Legal Basis',
        translate=True,
    )

    # =========================================================================
    # ПРОМЕНИ — ЗАПЛАТА
    # =========================================================================

    old_wage = fields.Monetary(
        string='Previous Wage',
        currency_field='currency_id',
        readonly=True,
    )

    new_wage = fields.Monetary(
        string='New Wage',
        currency_field='currency_id',
    )

    wage_change_reason = fields.Text(string='Wage Change Reason')

    wage_difference = fields.Monetary(
        string='Wage Difference',
        compute='_compute_wage_difference',
        currency_field='currency_id',
    )

    is_wage_increase = fields.Boolean(
        string='Wage Increase',
        compute='_compute_wage_difference',
    )

    # =========================================================================
    # ПРОМЕНИ — ПОЗИЦИЯ (НКПД)
    # =========================================================================

    old_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='Previous NKPD Code',
        readonly=True,
    )

    new_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='New NKPD Code',
    )

    # 🔑 Длъжността в Odoo е `hr.job`; НКПД и КИД СЛЕДВАТ от нея през компютите
    # на версията. Дотук ДС-то пишеше само квалификационната група — тоест
    # производното — и оставяше длъжността непокътната. Следствието е парично:
    # МОД се вади като „ред = КИД, колона = квалификационна група"; смени ли се
    # само колоната, излиза минимален осигурителен доход, който не отговаря на
    # нито една реална длъжност. Плюс бланката, която печата старата длъжност
    # до новия шифър.
    old_job_id = fields.Many2one(
        'hr.job',
        string='Previous Job Position',
        readonly=True,
    )

    new_job_id = fields.Many2one(
        'hr.job',
        string='New Job Position',
        help="The job position itself. NKPD code, KID and qualification group "
             "are derived from it — do not set them separately.",
    )

    # =========================================================================
    # ПРОМЕНИ — ИКОНОМИЧЕСКА ДЕЙНОСТ (КИД)
    # =========================================================================

    old_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='Previous Economic Activity',
        readonly=True,
    )

    new_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        string='New Economic Activity',
    )

    # =========================================================================
    # ПРОМЕНИ — РАБОТНО ВРЕМЕ
    # =========================================================================

    old_working_time_type = fields.Selection(selection=lambda self: self.env['hr.version'].fields_get(
            ['l10n_bg_working_time_type'])['l10n_bg_working_time_type']['selection'], string='Previous Working Time Type', readonly=True)

    new_working_time_type = fields.Selection(selection=lambda self: self.env['hr.version'].fields_get(
            ['l10n_bg_working_time_type'])['l10n_bg_working_time_type']['selection'], string='New Working Time Type')

    # 🔑 DEF-116/1б: ГРАФИКЪТ е носителят, часовете следват от него.
    #
    # Дотук ДС-то приемаше две числа и САМО намираше календар — първия запис с
    # две съвпадащи стойности. Измерено от Пламена: за 40/8 връщаше кал. 1
    # (0 версии) вместо кал. 22 (297 версии). Днес двата са идентични, тъй че
    # щета няма — но изборът стъпва на съвпадение на два скалара, докато
    # работните дни, часовата зона, двуседмичността и общокалендарните
    # отсъствия остават извън сравнението.
    old_resource_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Previous Working Schedule',
        readonly=True,
    )

    new_resource_calendar_id = fields.Many2one(
        'resource.calendar',
        string='New Working Schedule',
        help="The working time schedule itself. Daily and weekly hours are "
             "derived from it — do not state them separately. The pro-rated "
             "minimum insurance income is computed from this schedule.",
    )

    # Снимките на часовете ОСТАВАТ: те са историята на подписания документ.
    # Календарът е запис и може да бъде редактиран после; числата, щамповани
    # при одобрението, казват какво е било уговорено ТОГАВА. Същият довод като
    # при `l10n_bg_job_id` върху фишовия ред (ADR-0008).
    old_daily_hours = fields.Float(string='Previous Daily Hours', readonly=True)
    old_weekly_hours = fields.Float(string='Previous Weekly Hours', readonly=True)

    # =========================================================================
    # ПРОМЕНИ — РАБОТНО МЯСТО
    # =========================================================================

    # ⚠️ Двете Char полета остават САМО за печат и за заварените ДС-та.
    # Свободният текст не се резолвва надеждно към `hr.work.location`, тъй че
    # не се мигрира — виж M-F. Носителят е `*_work_location_id` по-долу.
    old_work_location = fields.Char(string='Previous Work Location', readonly=True)
    new_work_location = fields.Char(string='New Work Location')

    # 🔑 Работното място в Odoo е запис (`hr.work.location`), не текст, и носи
    # своя адрес. От адреса се вади ЕКАТТЕ кодът, който влиза в уведомлението
    # по чл. 62, ал. 5 КТ. Дотук ДС-то пишеше текст в производно поле, а
    # кодът оставаше копиран от предишната версия — тоест уведомлението
    # тръгваше със СТАРОТО населено място.
    old_work_location_id = fields.Many2one(
        'hr.work.location',
        string='Previous Work Location Record',
        readonly=True,
    )

    new_work_location_id = fields.Many2one(
        'hr.work.location',
        string='New Work Location Record',
        help="The work location record. Its address and the EKATTE code of "
             "the settlement follow from it.",
    )

    # =========================================================================
    # ПРОМЕНИ — ОТПУСКИ
    # =========================================================================

    old_leave_days = fields.Integer(string='Previous Leave Days', readonly=True)
    new_leave_days = fields.Integer(string='New Leave Days')

    # =========================================================================
    # ВРЕМЕННО ПРЕМЕСТВАНЕ (ЧЛ. 106-114 КТ)
    # =========================================================================

    is_temporary_assignment = fields.Boolean(string='Temporary Assignment')

    temporary_assignment_reason = fields.Selection([
        ('production_necessity', 'Production Necessity'),
        ('employee_replacement', 'Employee Replacement'),
        ('urgent_work', 'Urgent Work'),
        ('natural_disaster', 'Natural Disaster'),
        ('other_emergency', 'Other Emergency'),
    ], string='Assignment Reason')

    assignment_duration_months = fields.Integer(string='Assignment Duration (months)')
    assignment_location = fields.Char(string='Assignment Location')
    assignment_compensation = fields.Monetary(
        string='Assignment Compensation',
        currency_field='currency_id',
    )

    # =========================================================================
    # СТАТУС И ОДОБРЕНИЯ
    # =========================================================================

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancel', 'Cancelled'),
    ], string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    approved_by_id = fields.Many2one('res.users', string='Approved by', readonly=True)
    approved_date = fields.Datetime(string='Approval Date', readonly=True)

    signed_by_employee = fields.Boolean(string='Signed by Employee')
    signed_by_employer = fields.Boolean(string='Signed by Employer')

    # =========================================================================
    # ТЕХНИЧЕСКИ ПОЛЕТА
    # =========================================================================

    currency_id = fields.Many2one(
        related='version_id.currency_id',
        string='Currency',
        readonly=True,
    )

    notes = fields.Text(string='Internal Notes')

    # =========================================================================
    # COMPUTED
    # =========================================================================

    @api.depends('amendment_number', 'subject')
    def _compute_display_name(self):
        for rec in self:
            if rec.amendment_number and rec.amendment_number != _('New') and rec.subject:
                rec.display_name = f"{rec.amendment_number} - {rec.subject}"
            else:
                rec.display_name = rec.amendment_number or _('New Amendment')

    @api.depends('new_wage', 'old_wage')
    def _compute_wage_difference(self):
        for rec in self:
            if rec.new_wage and rec.old_wage:
                rec.wage_difference = rec.new_wage - rec.old_wage
                rec.is_wage_increase = rec.wage_difference > 0
            else:
                rec.wage_difference = 0.0
                rec.is_wage_increase = False

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================

    @api.constrains('date_signed', 'date_effective')
    def _check_dates(self):
        for rec in self:
            if rec.date_signed and rec.date_effective and rec.date_signed > rec.date_effective:
                raise ValidationError(
                    _("Signature date cannot be after effective date."))

    @api.constrains('date_effective', 'date_end')
    def _check_effective_dates(self):
        for rec in self:
            if rec.date_end and rec.date_effective and rec.date_effective >= rec.date_end:
                raise ValidationError(
                    _("Effective date must be before end date."))

    @api.constrains('assignment_duration_months')
    def _check_assignment_duration(self):
        for rec in self:
            if rec.is_temporary_assignment and rec.assignment_duration_months and rec.assignment_duration_months > 12:
                raise ValidationError(
                    _("Temporary assignment cannot exceed 12 months per Labor Code."))

    # =========================================================================
    # ORM
    # =========================================================================

    # Полетата, които ОПИСВАТ договореното. След като ДС-то е приложено, те са
    # история — смяната им би направила документа различен от онова, което
    # системата вече е записала по договора и е подала навън.
    # ⚠️ Нарочно НЕ включва служебните (`state`, `l10n_bg_register_id`,
    # `applied_version_id`, полетата за подпис и НАП статус): регистърът и
    # подписът пишат по активно ДС и това е законно.
    _L10N_BG_LOCKED_AFTER_ACTIVATION = (
        'version_id', 'amendment_type', 'date_signed', 'date_effective',
        'date_end', 'new_wage', 'new_job_id', 'new_position_id',
        'new_economic_activity_id', 'new_working_time_type',
        'new_resource_calendar_id', 'new_work_location', 'new_work_location_id',
        'new_leave_days',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('amendment_number', _('New')) == _('New'):
                vals['amendment_number'] = self.env['ir.sequence'].next_by_code(
                    'l10n_bg.hr.version.amendment') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        zaklyucheni = set(vals) & set(self._L10N_BG_LOCKED_AFTER_ACTIVATION)
        if zaklyucheni:
            prilozheni = self.filtered(
                lambda r: r.state in ('active', 'expired'))
            if prilozheni:
                raise ValidationError(_(
                    "Amendment %(ref)s is already in force; %(fields)s can no "
                    "longer be changed. Editing it would make the signed "
                    "document differ from the contract version it produced. "
                    "Create a new amendment instead.",
                    ref=prilozheni[0].amendment_number or prilozheni[0].id,
                    fields=", ".join(sorted(zaklyucheni))))
        return super().write(vals)

    # =========================================================================
    # ACTIONS
    # =========================================================================

    def action_submit_for_approval(self):
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_("Only draft amendments can be submitted."))
        # 🚨 DEF-175: проверката минава ТУК, а не чак при активирането.
        #
        # Дотук `_l10n_bg_validate_calendar` се викаше само от
        # `_apply_version_changes`, тоест на последната стъпка. Човекът минава
        # чернова → за одобрение → одобрено → в сила и получава отказа накрая,
        # когато документът вече е подписан и одобрен — а връщане назад по
        # машината на състоянията няма.
        #
        # 🔑 Ранната проверка не заменя късната: импортът и RPC не минават през
        # този бутон, тъй че гардът в прилагането ОСТАВА. Тук той само се
        # премества там, където още може да бъде поправен.
        self._l10n_bg_check_before_approval()
        self.state = 'to_approve'

    def _l10n_bg_check_before_approval(self):
        """Каквото може да се провери ПРЕДИ подписа — проверява се тук.

        Правилото: гард, който отказва на последната стъпка, спира законна
        работа без изход. Всичко, което зависи само от съдържанието на ДС-то
        (а не от състоянието на версията в мига на прилагане), принадлежи на
        тази проверка.
        """
        self.ensure_one()
        if self._l10n_bg_changes_working_time():
            self._l10n_bg_validate_calendar()

    def action_approve(self):
        self.ensure_one()
        if self.state != 'to_approve':
            raise ValidationError(_("Only amendments pending approval can be approved."))
        vals = {
            'state': 'approved',
            'approved_by_id': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        }
        # Щампова „предишната стойност" при одобрението. onchange-ът лови
        # само пътя през интерфейса — при импорт или RPC old_* оставаха
        # празни и бланката излизаше без предишната стойност. Пълним само
        # незаетите, за да не се презапише ръчно въведена стойност.
        vals.update({
            field_name: value
            for field_name, value in self._snapshot_old_values().items()
            if not self[field_name]
        })
        self.write(vals)

    def action_activate(self):
        """Активиране на настъпило ДС. Кронът минава оттук."""
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_("Only approved amendments can be activated."))
        dnes = fields.Date.context_today(self)
        if self.date_effective and self.date_effective > dnes:
            # Предсрочното не изплаща по-рано (версията носи своята дата), но
            # прави документа „в сила" преди уговореното и не оставя следа кой
            # го е решил. Затова има отделно действие.
            raise ValidationError(_(
                "Amendment %(ref)s takes effect on %(effective)s, which has "
                "not arrived yet. It will be activated automatically on that "
                "day. If it must take effect now, use 'Activate Early' — that "
                "action is recorded in the chatter.",
                ref=self.amendment_number or self.id,
                effective=self.date_effective))
        self._l10n_bg_do_activate()

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
                "date %(effective)s.",
                today=dnes, effective=self.date_effective))

    def _l10n_bg_do_activate(self):
        """Общото тяло: проверките и прилагането са на едно място."""
        self.ensure_one()
        self._l10n_bg_check_backdating()
        self._apply_version_changes()
        self.state = 'active'

    @api.depends('date_effective')
    def _compute_l10n_bg_effective_in_future(self):
        dnes = fields.Date.context_today(self)
        for rec in self:
            rec.l10n_bg_effective_in_future = bool(
                rec.date_effective and rec.date_effective > dnes)

    def _l10n_bg_check_backdating(self):
        """Кука: отказва връщане назад в ЗАТВОРЕН период.

        🔑 Базовият модул НЕ зависи от ведомостта (`depends`: hr, mail,
        l10n_bg_config, l10n_bg_payroll_classifications), тъй че тук няма как
        да се знае кое е затворено. Слоят с ведомостта override-ва този метод
        и отказва при валидиран фиш за периода. Виж ADR-0006.

        Корекция назад е нормална работа на ТРЗ и НЕ се забранява по принцип —
        отказът принадлежи само там, където нещо вече е излязло навън.
        """
        return

    def action_cancel(self):
        self.ensure_one()
        if self.state in ('active', 'expired'):
            raise ValidationError(_("Cannot cancel active or expired amendments."))
        self.state = 'cancel'

    # Състоянията, от които има връщане назад (DEF-175б).
    #
    # „В сила" и „изтекло" НЕ са между тях, и това не е пропуск: гардът в
    # ``write`` правилно забранява промяна на заключените полета там, защото
    # подписаният документ би се разминал с версията, която е родил.
    _L10N_BG_STATES_WITH_A_WAY_BACK = ('draft', 'to_approve', 'approved',
                                       'cancel')

    def action_draft(self):
        """DEF-175б — от гардовете имаше отказ, но нямаше връщане.

        Състоянията са чернова → за одобрение → одобрено → в сила или изтекло,
        плюс отказано. Действие за връщане в чернова нямаше, нито бутон.

        Изиграно от Пламена: ДС 345 е създадено без график, подадено, одобрено —
        и чак при активирането отказа. После графикът е попълнен, активирането
        пак пада, този път по друга причина, и остава само отказът. Всяка
        засечка значи НОВО ДС с нов номер по същия подписан документ, а
        ``ir.sequence`` не се връща.

        🔑 Затова връщането не е удобство, а изход. Гардовете вече отказват
        рано (DEF-175а); без път назад ранният отказ само мести задънената улица
        по-напред.
        """
        self.ensure_one()
        if self.state not in self._L10N_BG_STATES_WITH_A_WAY_BACK:
            raise ValidationError(_(
                "Amendment %(ref)s is %(state)s and cannot go back to draft. "
                "The signed document would differ from the contract version it "
                "produced. Create a new amendment instead.",
                ref=self.amendment_number or self.id,
                state=dict(self._fields['state'].selection).get(self.state)))
        if self.state == 'draft':
            return
        predi = self.state
        self.state = 'draft'
        self.message_post(body=_(
            "Reset to draft from %(state)s.",
            state=dict(self._fields['state'].selection).get(predi)))

    # =========================================================================
    # BUSINESS LOGIC
    # =========================================================================

    def _l10n_bg_changes_working_time(self):
        """Мени ли това ДС договореното работно време (DEF-116)."""
        self.ensure_one()
        if self.amendment_type == 'working_time_change':
            return True
        return bool(
            (self.new_working_time_type
             and self.new_working_time_type != self.old_working_time_type)
            or (self.new_resource_calendar_id
                and self.new_resource_calendar_id != self.old_resource_calendar_id)
        )

    def _l10n_bg_validate_calendar(self):
        """Избраният график вътрешно непротиворечив ли е — или отказ.

        DEF-116/1б: методът вече НЕ избира. Дотук намираше първия календар с
        две съвпадащи числа; сега ДС-то носи графика си изрично и тук остава
        само проверката, заради която търсенето беше двойно.

        🚨 Календар, чиито дневни часове не се връзват с присъствията му, е
        капан: „График непълно раб.време - 4ч." носи `hours_per_day = 4` при
        присъствия 08:00–17:00, а фишът дели 168 ÷ 4 и дава 42 отработени дни
        в месец с 21. Пламена изрично предупреди да не се стъпва на едното
        число.

        🔑 Сборът минава през ядрените помощници, НЕ през суров
        `hour_to - hour_from`: `_get_global_attendances()` изхвърля редовете с
        `day_period = 'lunch'`. Стоковият календар носи пет обедни реда
        12:00–13:00 и суровият сбор дава 45 при договорени 40.
        """
        self.ensure_one()
        calendar = self.new_resource_calendar_id
        if not calendar:
            raise ValidationError(_(
                "Amendment %(ref)s changes the working time but states no "
                "schedule. Pick the new working schedule — it determines both "
                "the working time calendar and the pro-rated minimum "
                "insurance income.",
                ref=self.amendment_number or self.id))

        # Гъвкавият календар няма фиксирани присъствия и ядрото НЕ му
        # компютира часовете — проверката за съгласуваност е безсмислена.
        if calendar.flexible_hours:
            return calendar

        dnevni = calendar._get_hours_per_day()
        sedmichni = calendar._get_hours_per_week()
        if not dnevni or not sedmichni:
            raise ValidationError(_(
                "Schedule %(cal)s states no working hours. The pro-rated "
                "minimum insurance income cannot be computed from it.",
                cal=calendar.display_name))

        # Пет работни дни е допускането, при което двете числа трябва да се
        # връзват. 🔲 Норма с друг брой работни дни иска решение, не догадка —
        # затова тук се ОТКАЗВА явно, вместо да се приеме мълчаливо.
        if abs(sedmichni - dnevni * 5.0) > 0.01:
            raise ValidationError(_(
                "Schedule %(cal)s is internally inconsistent: %(daily).2f "
                "hours per day do not match its %(weekly).2f weekly "
                "attendance hours. A payslip dividing by the daily figure "
                "would report more worked days than the month has. Fix the "
                "schedule, then activate the amendment again.",
                cal=calendar.display_name, daily=dnevni, weekly=sedmichni))
        return calendar

    # Типовете, чието съдържание е ТЕКСТ, а не величина по договора.
    # За тях `vals` е празен по конструкция и това не е дефект.
    _L10N_BG_TEXTUAL_TYPES = ('other', 'additional_duties')

    def _l10n_bg_is_textual(self):
        """Договореното при този тип е описание, не стойност по договора."""
        self.ensure_one()
        return (self.amendment_type in self._L10N_BG_TEXTUAL_TYPES
                and bool(self.description))

    def _l10n_bg_apply_textual(self):
        """Текстово споразумение: следа върху действащата версия, без нова.

        Раждането на версия без нито една променена стойност би описало промяна,
        каквато няма — и би разцепило месеца във фиша за нищо. Затова тук се
        записва само следата, а `applied_version_id` сочи версията, действала на
        датата на влизане в сила.
        """
        self.ensure_one()
        employee = self.version_id.employee_id
        version = (employee._get_version(self.date_effective)
                   if self.date_effective else False) or self.version_id
        version.message_post(
            body=_("Amendment %(ref)s in force from %(date)s: %(text)s",
                   ref=self.amendment_number or self.id,
                   date=self.date_effective,
                   text=self.description),
            subject=_("Contract Amendment"))
        self.applied_version_id = version
        return version

    def _apply_version_changes(self):
        """Apply amendment changes as a NEW version starting on the effective date."""
        self.ensure_one()

        # Гардът срещу срочните ДС ОТПАДА: изходът вече ражда НОВА версия от
        # `date_end + 1`, вместо да презаписва текущата. Входът и изходът са
        # симетрични — и двата минават през `create_version`.
        if (self.is_temporary or self.is_temporary_assignment) and not self.date_end:
            raise ValidationError(_(
                "Amendment %(ref)s is temporary but has no end date. Without "
                "it the change would stay in force forever — the expiry cron "
                "looks for the end date.",
                ref=self.amendment_number or self.id))

        vals = {}

        if self.new_wage:
            vals['wage'] = self.new_wage
        if self.new_job_id:
            # Длъжността е носителят; НКПД, КИД и квалификационната група се
            # ПРОИЗВЕЖДАТ от нея. Затова групата НЕ се пише тук — записът ѝ
            # би се борил със собствения ѝ компют и `action_refresh_nkpd_kid`
            # би я върнал.
            vals['job_id'] = self.new_job_id.id
        elif self.new_position_id:
            # Заварен път: ДС само с НКПД класификация, без длъжност. Пази се
            # за старите записи, но новите минават през `new_job_id`.
            vals['l10n_bg_qualification_group'] = self.new_position_id.id
            # 🚨 Записът е ОБРЕЧЕН: групата е computed+stored по `job_id`, тъй
            # че първото опресняване я връща. Досега това ставаше тихо — сега
            # остава следа там, където човекът я търси. Не се вдига грешка:
            # заварените ДС-та трябва да могат да се активират.
            _logger.warning(
                "Amendment %s changes only the NKPD code (%s); job position "
                "stays %s. The code is derived from the job and will be "
                "restored on the next refresh.",
                self.amendment_number or self.id,
                self.new_position_id.display_name,
                self.version_id.job_id.display_name or '-')
            self.message_post(body=_(
                "This amendment changed only the NKPD code to %(code)s. The "
                "job position stays %(job)s, and the code is derived from it "
                "— the next refresh will restore %(old)s together with the "
                "minimum insurance income. Set the job position instead.",
                code=self.new_position_id.display_name,
                job=self.version_id.job_id.display_name or '-',
                old=(self.version_id.job_id.l10n_bg_ncop_position_id
                     .display_name or '-')))
        if self.new_economic_activity_id:
            vals['l10n_bg_economic_activity_id'] = self.new_economic_activity_id.id
        if self.new_working_time_type:
            vals['l10n_bg_working_time_type'] = self.new_working_time_type
        if self.new_work_location_id:
            # Локацията и адресът вървят заедно — ядреният домейн на
            # `work_location_id` е `[('address_id', '=', address_id)]`, тъй че
            # запис само на едното дава несъгласувана двойка.
            vals['work_location_id'] = self.new_work_location_id.id
            vals['address_id'] = self.new_work_location_id.address_id.id
            # 🚨 ЕКАТТЕ кодът се КОПИРА при раждането на версията, а резолверът
            # излиза рано, щом полето е попълнено. Без това зануляване новата
            # версия носи кода на СТАРОТО населено място и уведомлението по
            # чл. 62, ал. 5 КТ тръгва с него.
            vals['l10n_bg_workplace_code'] = False
        elif self.new_work_location:
            # Текстовото поле на версията е related+readonly към адреса на
            # локацията — записът в него не оцелява първото преизчисление.
            # Не се пише; казва се защо, вместо да мълчи.
            _logger.warning(
                "ДС %s носи работно място само като текст (%r). Текстът НЕ е "
                "носител — попълни „Ново работно място“ (запис), за да се "
                "смени и ЕКАТТЕ кодът в уведомлението.",
                self.amendment_number, self.new_work_location)
        if self.new_leave_days:
            vals['l10n_bg_basic_leave_days'] = self.new_leave_days

        # 🚨 DEF-116 т.1в — „Удължаване на срока" приемаше дата и не удължаваше
        # нищо. Грепнат целият модел: нито `contract_date_end`, нито
        # `l10n_bg_fixed_term_end` се срещаха при прилагането.
        #
        # ⚖️ Записва се СРОКЪТ, не прекратяването (ADR-0017). Чл. 68 КТ дава
        # уговорен срок, който може да изтече, без някой да прекрати; тогава
        # чл. 69, ал. 1 действа сам. `contract_date_end` е прекратяването и не
        # се пипа оттук.
        if (self.amendment_type == 'contract_extension' and self.date_end
                and 'l10n_bg_fixed_term_end' in self.version_id._fields):
            vals['l10n_bg_fixed_term_end'] = self.date_end

        # DEF-116: ДС за работно време СМЕНЯ и календара, или отказва.
        #
        # Досега се пренасяше само ЕТИКЕТЪТ (`l10n_bg_working_time_type`) и
        # часовете, а `resource_calendar_id` оставаше пълният 8-часов. Оттам
        # прората на МОД не пали — тя гледа календара — и минималният
        # осигурителен доход излиза ЦЯЛ.
        #
        # Мерено в plm_acc: две версии носят „непълно работно време" с 20
        # седмични часа при 8-часов календар и дават МОД 620,20 вместо 310,10.
        # Двойно, и то мълчаливо.
        if self._l10n_bg_changes_working_time():
            calendar = self._l10n_bg_validate_calendar()
            vals['resource_calendar_id'] = calendar.id
            # 🚨 Часовете на версията се ИЗВЕЖДАТ от графика, не се наследяват.
            #
            # Без този блок новата версия копира `l10n_bg_weekly_hours` от
            # старата: календарът казва 20 ч, а полето — 40. Парите оцеляват,
            # защото клон 1 на `_l10n_bg_mod_prorata` гледа календара — но ние
            # сами раждаме противоречието в данните, което клон 2 е построен
            # да ЛОВИ, и го предаваме на `hr_seniority_period` (прагът на
            # стажа) и на `@api.constrains` върху двете полета.
            if not calendar.flexible_hours:
                if 'l10n_bg_daily_hours' in self.version_id._fields:
                    vals['l10n_bg_daily_hours'] = calendar._get_hours_per_day()
                if 'l10n_bg_weekly_hours' in self.version_id._fields:
                    vals['l10n_bg_weekly_hours'] = calendar._get_hours_per_week()

        if not vals and self._l10n_bg_is_textual():
            # 🚨 DEF-116 т.1в — „Друго" и „Допълнителни задължения" НЯМАТ
            # собствено поле, което да мени версията. `vals` при тях е празен по
            # конструкция, тъй че отказът по-долу ги правеше неприложими при
            # каквито и да е обстоятелства. Изиграно с ДС 354.
            #
            # ⚖️ Договореното е текст, не величина: допълнителни задължения без
            # промяна на възнаграждението са редовно споразумение по чл. 119 КТ.
            # Затова НЕ се ражда версия — раждането ѝ би описало промяна, каквато
            # няма. Следата отива в чатъра на версията, действала на датата.
            return self._l10n_bg_apply_textual()

        if not vals:
            # 🚨 Дотук се излизаше ТИХО, а извикващият вдигаше състоянието на
            # „в сила". Резултатът: подписано споразумение, което системата
            # смята за приложено, а по договора не е сменено нищо. Явният
            # отказ е по-евтин от документ, който лъже.
            raise ValidationError(_(
                "Amendment %(ref)s does not change anything on the contract. "
                "Fill in at least one new value — wage, job position, work "
                "location, working time or leave days — or cancel it. An "
                "amendment cannot take effect without a change.",
                ref=self.amendment_number or self.id))

        # Промяната ражда НОВА версия от датата на влизане в сила, вместо да
        # презаписва текущата. Иначе увеличение с бъдеща дата важи и назад, а
        # преизчисляване на минал период (Д1 корекция, УП-2, регенерация на
        # регистъра) чете новата стойност като валидна открай време.
        # 🚨 Полета с copy=False се губят: create_version стъпва на copy_data().
        # `copy=False` е предвидено за ДУБЛИРАНЕ на версия (нов договор), но при
        # допълнително споразумение договорът е СЪЩИЯТ — номерът му продължава.
        #
        # 🚨 DEF-122 т.1 — пренасяше се от ПОСОЧЕНАТА версия, а фактът стои в
        # онази, в която пада ДАТАТА. ТРЗ мисли в дати, не във версии: визардът
        # слага `employee.version_id` по подразбиране и се сменя само датата.
        #
        # Мерено от Пламена, служител 1087 с версии 1120 (01.09–14.09),
        # 1121 (01.10–12.11) и 1122 (13.11–):
        #   · ДС 343 сочи 1121, дата 15.09 → пада в 1120, ражда се 1239 —
        #     но класовият период излиза 29:06:05, стойността на 1121;
        #   · ДС 356 сочи 1120, дата 01.10 → пада в 1121, прилага се вярно —
        #     и carried пренася периода на 1120 ВЪРХУ 1121. Двете средни
        #     версии на този служител вече са разменени.
        #
        # Класовият период ОТПАДА оттук изцяло: `hr.version.create` в слоя с
        # ведомостта вече го решава по дата (`_l10n_bg_inherited_class_period`)
        # и дава верния отговор — `carried` само минаваше отгоре. Останалите две
        # нямат резолвер и не могат просто да отпаднат, защото са `copy=False`;
        # затова се четат от версията, в която пада датата.
        employee = self.version_id.employee_id
        iztochnik = (employee._get_version(self.date_effective)
                     if self.date_effective else False) or self.version_id
        carried = {}
        for field_name in ('l10n_bg_unrecognized_company_is_manual',
                           'l10n_bg_contract_number'):
            if field_name in iztochnik._fields:
                carried[field_name] = iztochnik[field_name]

        # 🚨 DEF-175в — смяната на графика влачеше ЦЯЛАТА история на отпуските.
        #
        # `hr_holidays` преизчислява отпуските при смяна на календара, а взима
        # прозореца на ДОГОВОРА (`contract_date_start` / `contract_date_end`),
        # не на версията. Оттам ядреният `_check_date_state` отказва всяка
        # промяна по отпуск в състояние „одобрен" и ДС-то пада.
        #
        # Носител на Пламена: служител 902 има отпуск 341 за 18–30.12.2025 в
        # състояние „validate"; ДС за септември 2026 беше отказано заради него.
        # На същата база 261 от 311 активни служители имат поне един одобрен
        # отпуск — тоест на практика цялата ведомост.
        #
        # ⚖️ Ключът `leave_skip_state_check` на ядрото само ЗАГЛУШАВА проверката;
        # декемврийският отпуск пак щеше да се преизчисли по нов календар, който
        # тогава не е действал. Затова стесняваме прозореца: изменение, действащо
        # от дадена дата, няма работа с отпуск отпреди нея.
        ctx = {'l10n_bg_amendment_window': (
            self.date_effective, self.date_end or False)}
        employee = employee.with_context(**ctx)
        new_version = employee.create_version(
            dict(vals, date_version=self.date_effective))
        new_version = new_version.with_context(**ctx)
        if carried:
            new_version.write(carried)
        # 🚨 create_version излиза рано и НЕ прилага стойностите, когато вече
        # съществува версия с тази дата — тогава връща нея непокътната. Без
        # изричния write ДС-то минава в „в сила", а заплатата не се сменя, тихо.
        new_version.write(vals)
        # Записва се СЛЕД `write`, за да сочи версия, която вече носи
        # стойностите. Ако `create_version` е излязъл рано и е върнал
        # съществуваща версия, приложената е точно тя — това е верният адрес,
        # не отклонение.
        self.applied_version_id = new_version
        new_version.message_post(
            body=_('Created by amendment %s') % self.amendment_number,
            subject=_('Contract Amendment Applied'),
        )

    def _l10n_bg_effective_version(self):
        """Версията, която ДС-то ОПИСВА — за справки, декларации и бланки.

        Активирано ДС сочи родената версия; неактивирано още няма такава и
        остава изходната, за да може бланката да се печата предварително.
        Едно място, вместо `applied_version_id or version_id` навсякъде.
        """
        self.ensure_one()
        return self.applied_version_id or self.version_id

    @api.model
    def cron_activate_due_amendments(self):
        """Активира одобрените ДС, чиято дата на влизане в сила е настъпила.

        Активирането беше само ръчен бутон. ДС се подписва предварително, с
        бъдеща дата, и между одобрението и датата минават седмици — пропусне
        ли се натискането, фишът излиза със старата заплата и мълчи.
        Симетрично на cron_expire_temporary_amendments: ако изтичането върви,
        а активирането не, срочните ДС ще изтичат, без изобщо да са влизали
        в сила.
        """
        today = fields.Date.today()
        # 🚨 Редът е ЧАСТ ОТ ВЕРНОСТТА, не козметика. `_order` на модела е
        # `date_signed desc` — тоест последно подписаното излиза първо. А
        # `action_activate` вика `create_version(date_version=date_effective)`,
        # който копира версията, ДЕЙСТВАЩА на тази дата. Активира ли се
        # по-късното ДС преди по-ранното, то копира състоянието ОТПРЕДИ
        # по-ранното и заплатата от по-късната дата се връща на старата;
        # увеличението живее само в прозореца между двете дати.
        # Затова се активира в реда, в който промените влизат в сила.
        due = self.search([
            ('state', '=', 'approved'),
            ('date_effective', '<=', today),
        ], order='date_effective asc, id asc')
        for amendment in due:
            # Грешка от едно ДС не спира партидата — остава в „Одобрено"
            # с бележка в чата, за да се види от кого се чака намеса.
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
        """Expire temporary amendments past their end date."""
        today = fields.Date.today()
        expired = self.search([
            ('state', '=', 'active'),
            ('is_temporary', '=', True),
            ('date_end', '<=', today),
        ])
        for rec in expired:
            rec.state = 'expired'
            # 🚨 DEF-104Б А.2 — гардът беше на ГРЕШНИЯ флаг. Търсенето отгоре
            # вече реже по `is_temporary` (срочност), а тук се питаше
            # `is_temporary_assignment` (ТИП — временно преместване). Срочно ДС
            # по чл. 119, ал. 1 КТ има срочност, но няма тип, тъй че кронът го
            # обявяваше за изтекло и не връщаше НИЩО.
            #
            # ⚖️ Чл. 119, ал. 1 КТ говори за изменение „за определено време",
            # чл. 120 — за „временно". И в двата случая изтичането трябва да
            # върне предишното; типът не е признакът, срочността е.
            rec._l10n_bg_revert_temporary()

    def _l10n_bg_wage_still_ours(self):
        """Заплатата днес още ли е онази, която ТОВА ДС е поставило.

        Връщането при изтичане е валидно само докато ефектът на споразумението
        стои. Ако междувременно друго ДС е вдигнало заплатата, връщането към
        `old_wage` би било мълчаливо намаление на възнаграждение, за което има
        подписан документ.

        Празно `new_wage` значи, че това ДС изобщо не е пипало заплатата —
        тогава няма какво да се връща.
        """
        self.ensure_one()
        if not self.new_wage:
            return False
        # Въпросът е „към момента на ИЗТИЧАНЕТО", не „днес": кронът може да
        # хване ДС дни по-късно, а дотогава да е влязла съвсем друга версия.
        employee = self.version_id.employee_id
        v_sila = employee._get_version(self.date_end) if self.date_end else employee.version_id
        tekushta = (v_sila or employee.version_id).wage
        if float_compare(tekushta, self.new_wage, precision_digits=2) == 0:
            return True
        self.message_post(body=_(
            "Wage not restored on expiry: it is now %(current).2f, while this "
            "amendment set %(ours).2f. A later change is in force; restoring "
            "%(previous).2f would silently cut it.",
            current=tekushta, ours=self.new_wage, previous=self.old_wage))
        return False

    def _l10n_bg_revert_temporary(self):
        """Изтичането ражда НОВА версия от `date_end + 1` с върнатите стойности.

        🔑 Симетрично на прилагането. Дотук изходът пишеше ВЪРХУ изходната
        версия — тоест командироването изчезваше от историята, сякаш никога не
        е било, а периодът, в който човекът е бил на друга длъжност, оставаше
        неописан. Новата версия го затваря на своята дата.

        ⚖️ Връщат се СЪЩИТЕ носители, които прилагането е сменило: длъжността
        (или заварената квалификационна група), работното място с адреса и
        ЕКАТТЕ, икономическата дейност — и ЗАПЛАТАТА.

        🚨 DEF-104Б А.2: дотук заплатата не се връщаше, а `old_wage` стоеше
        неизползвано. Обосновката беше „при временно преместване тя е предмет
        на отделна уговорка". Не е: чл. 267, ал. 3 КТ казва, че при друга
        работа поради производствена необходимост се плаща възнаграждението за
        изпълняваната работа, но не по-малко от брутното за основната. Това е
        последица от закона, обвързана с ПЕРИОДА — свърши ли периодът, отпада и
        основанието. Мерено: служител 902, ДС 342 — заплатата остана 1000,00
        вместо да се върне на 613,56.

        🔑 Заплатата се връща само ако още стои онова, което ТОВА ДС я е
        направило. Смени ли я по-късно друго ДС, връщането би било мълчаливо
        намаление; тогава не се пипа и причината влиза в чатъра.

        🔲 Същата фигура важи и за длъжността, мястото и дейността — там
        връщането е безусловно от самото начало. Не се пипа в тази промяна:
        поведението е заварено, няма измерен носител и разширяването би
        излязло извън искането. Докладвано отделно.
        """
        self.ensure_one()
        revert = {}
        if self.old_wage and self._l10n_bg_wage_still_ours():
            revert['wage'] = self.old_wage
        if self.old_job_id:
            revert['job_id'] = self.old_job_id.id
        elif self.old_position_id:
            revert['l10n_bg_qualification_group'] = self.old_position_id.id
        if self.old_work_location_id:
            revert['work_location_id'] = self.old_work_location_id.id
            revert['address_id'] = self.old_work_location_id.address_id.id
            revert['l10n_bg_workplace_code'] = False
        if self.old_economic_activity_id:
            revert['l10n_bg_economic_activity_id'] = self.old_economic_activity_id.id
        if not revert or not self.date_end:
            return self.env['hr.version']

        employee = self.version_id.employee_id
        nova = employee.create_version(
            dict(revert, date_version=self.date_end + timedelta(days=1)))
        # Същият изричен запис като при прилагането: `create_version` излиза
        # рано, когато вече има версия с тази дата, и връща нея непокътната.
        nova.write(revert)
        nova.message_post(
            body=_('Temporary amendment %s expired') % self.amendment_number,
            subject=_('Temporary Assignment Ended'),
        )
        self.message_post(body=_(
            "Expired on %(date)s; version %(version)s restores the previous "
            "terms.", date=self.date_end, version=nova.display_name))
        return nova

    def get_amendment_summary(self):
        """Какво мени това ДС — на човешки език (DEF-116 т.1г).

        Резюмето се чете на два екрана и на хартия: полето „Промени" на картона
        на служителя и бланката на самото споразумение. Три неща не бяха наред.

        🚨 **Графикът липсваше.** ``new_resource_calendar_id`` слезе на
        01.09.2026 по DEF-116 т.1б и стана НОСИТЕЛЯТ на работното време, но
        резюмето изброяваше шест величини без него. Мерено от Пламена: ДС 348 и
        346 менят само графика и дават резюме '' — празно, и на екрана, и на
        хартията.

        🚨 **Нямаше проверка за равенство.** ДС 344 с еднакви стари и нови
        стойности пишеше „Заплата: 1517.60 → 1517.60", тоест отчиташе промяна
        там, където няма.

        🚨 **Списъчните полета печатаха технически стойности** — „Работно време:
        full_time → part_time" вместо етикетите. Етикетът минава през превод,
        техническата стойност — не; на хартията излизаше английски идентификатор.

        🔑 И работното място вече се чете от ЗАПИСА, когато го има. Текстовите
        полета са заварени (DEF-172а) и не са носител.
        """
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
        # Длъжността е носителят и върви ПРЕДИ шифъра — резюмето се чете и
        # в бланката, където редът на двете определя кое човекът приема за
        # същинската промяна.
        if self.new_job_id and self.old_job_id != self.new_job_id:
            changes.append(_('Job Position: %(old)s → %(new)s',
                             old=self.old_job_id.name or '-',
                             new=self.new_job_id.name))
        if self.new_position_id and self.old_position_id != self.new_position_id:
            changes.append(_('NKPD Code: %(old)s → %(new)s',
                             old=self.old_position_id.name or '-',
                             new=self.new_position_id.name))
        if (self.new_work_location_id
                and self.old_work_location_id != self.new_work_location_id):
            changes.append(_('Work Location: %(old)s → %(new)s',
                             old=self.old_work_location_id.display_name or '-',
                             new=self.new_work_location_id.display_name))
        elif (self.new_work_location
                and self.old_work_location != self.new_work_location):
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
        if (self.new_resource_calendar_id
                and self.old_resource_calendar_id != self.new_resource_calendar_id):
            changes.append(_('Working Schedule: %(old)s → %(new)s',
                             old=self.old_resource_calendar_id.display_name or '-',
                             new=self.new_resource_calendar_id.display_name))
        if self.new_leave_days and self.old_leave_days != self.new_leave_days:
            changes.append(_('Leave Days: %(old)d → %(new)d',
                             old=self.old_leave_days, new=self.new_leave_days))
        return '\n'.join(changes)

    # =========================================================================
    # ONCHANGE
    # =========================================================================

    def _snapshot_old_values(self):
        """Текущите стойности на свързаната версия като vals за old_* полетата.

        Ползва се и от onchange-а (UI), и от одобрението (импорт/RPC) —
        иначе историята на ДС-то остава без „предишна стойност", а точно
        тя се печата в бланката."""
        self.ensure_one()
        v = self.version_id
        if not v:
            return {}
        return {
            'old_wage': v.wage,
            'old_job_id': v.job_id.id,
            'old_work_location_id': v.work_location_id.id,
            'old_position_id': v.l10n_bg_qualification_group.id,
            'old_economic_activity_id': v.l10n_bg_economic_activity_id.id,
            'old_working_time_type': v.l10n_bg_working_time_type,
            'old_resource_calendar_id': v.resource_calendar_id.id,
            'old_daily_hours': v.l10n_bg_daily_hours,
            'old_weekly_hours': (v.l10n_bg_weekly_hours
                                 if 'l10n_bg_weekly_hours' in v._fields else 40.0),
            'old_work_location': v.work_location or '',
            'old_leave_days': v.l10n_bg_total_leave_days,
        }

    @api.onchange('version_id')
    def _onchange_version_id(self):
        """Load current values from the linked version."""
        if self.version_id:
            for field_name, value in self._snapshot_old_values().items():
                self[field_name] = value

    @api.onchange('new_job_id')
    def _onchange_new_job_id_preview_nkpd(self):
        """Показва шифъра, който ЩЕ произтече от длъжността.

        Огледало на `hr.version._compute_l10n_bg_qualification_group`: пише се
        само когато длъжността носи НКПД — иначе версията също няма да смени
        нищо и празно поле би обещало промяна, която не идва.
        """
        if self.new_job_id and self.new_job_id.l10n_bg_ncop_position_id:
            self.new_position_id = self.new_job_id.l10n_bg_ncop_position_id
        if self.new_job_id and self.new_job_id.l10n_bg_economic_activity_id:
            # КИД идва по същия път; МОД се вади „ред = КИД, колона = група",
            # тъй че показването само на едното крие половината от ефекта.
            self.new_economic_activity_id = (
                self.new_job_id.l10n_bg_economic_activity_id)

    @api.onchange('new_position_id')
    def _onchange_new_position_id_warn_code_only(self):
        """ДС само с шифър пипа производното, не носителя.

        Предупреждение, не забрана: заварената пътека остава проходима за
        старите записи и за импорта.
        """
        if self.new_position_id and not self.new_job_id:
            return {'warning': {
                'title': _("NKPD code without a job position"),
                'message': _(
                    "This amendment changes only the NKPD code, not the job "
                    "position. The code is derived from the job position, so "
                    "the next refresh will silently restore it — together "
                    "with the minimum insurance income, which is read as "
                    "'row = KID, column = qualification group'. Set the job "
                    "position instead and let the code follow."),
            }}

    @api.onchange('amendment_type')
    def _onchange_amendment_type(self):
        if self.amendment_type == 'temporary_assignment':
            self.is_temporary = True
            self.is_temporary_assignment = True
        else:
            self.is_temporary_assignment = False

    @api.onchange('is_temporary')
    def _onchange_is_temporary(self):
        if not self.is_temporary:
            self.date_end = False
