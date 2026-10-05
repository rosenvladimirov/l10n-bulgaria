# -*- coding: utf-8 -*-
"""Картонът на служителя — частта по КТ, без ведомост.

Под „ИЗНЕСЕНО ОТ ТРЗ“ — пренесено от `l10n_bg_hr_payroll` 18.0.18.11.0 с
еднакви имена (related към активния договор, без колони).

Под „НОВО ОТ 19“ — полетата, които в 19 живеят на `hr.version` и се виждат през
служителя. В 18 версии няма, тъй че личните данни и документите са на
`hr.employee` — те са на лицето, не на договора.
"""
import logging
from datetime import timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Заявка Полигруп (28.08.2026): уведомление три месеца по-рано за всички
    # документи — един срок за всички.
    _L10N_BG_DOCUMENT_LEAD_DAYS = 90

    # =========================================================================
    # ИЗНЕСЕНО ОТ ТРЗ — КИД, НКПД ОТ АКТИВНИЯ ДОГОВОР
    # =========================================================================

    l10n_bg_ncop_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        related='contract_id.l10n_bg_ncop_position_id',
        readonly=True,
        string='NCOP Position',
    )

    l10n_bg_qualification_group = fields.Selection(
        related='contract_id.l10n_bg_qualification_group',
        readonly=True,
        string='NCOP',
    )

    l10n_bg_economic_activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity',
        related='contract_id.l10n_bg_economic_activity_id',
        readonly=True,
        string='NACE',
    )

    def action_refresh_nkpd_kid(self):
        """Copy NCOP position (and KID, when the job has one) from the job
        position to the active contract.

        В 18 НКПД идва от длъжността (`l10n_bg_payroll_classifications`).
        КИД на длъжността е ново поле (от 19) — пише се само ако е попълнено.
        """
        for employee in self:
            contract = employee.contract_id
            if not contract or not employee.job_id:
                continue
            vals = {}
            if employee.job_id.l10n_bg_ncop_position_id:
                vals['l10n_bg_ncop_position_id'] = employee.job_id.l10n_bg_ncop_position_id.id
            if employee.job_id.l10n_bg_economic_activity_id:
                vals['l10n_bg_economic_activity_id'] = employee.job_id.l10n_bg_economic_activity_id.id
            if vals:
                contract.write(vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Refreshed'),
                'message': _('NCOP position refreshed from job position.'),
                'type': 'success',
                'sticky': False,
            },
        }

    # =========================================================================
    # НОВО ОТ 19 — КИД КОД И КОД НА РАБОТНОТО МЯСТО
    # =========================================================================

    l10n_bg_economic_activity_code = fields.Char(
        string='Economic Activity Code',
        related='l10n_bg_economic_activity_id.code',
        readonly=True,
        help='Economic activity code according to KID 2008',
    )

    l10n_bg_workplace_code = fields.Char(
        string='Workplace Code (EKATTE)',
        groups='hr.group_hr_user',
        tracking=True,
        help='Workplace location code according to EKATTE',
    )

    # =========================================================================
    # НОВО ОТ 19 — ЛИЧНИ ДОКУМЕНТИ И СРОКОВЕТЕ ИМ
    # =========================================================================
    # Ядрото на 18 носи визата и разрешението за работа със сроковете им; няма
    # лична карта, нито закрила, нито срок на паспорта. Уведомлението чете и
    # ядрените, и нашите срокове от ЕДИН списък — `_l10n_bg_document_expiries`.

    l10n_bg_id_card_number = fields.Char(
        string='ID Card No', groups='hr.group_hr_user', tracking=True,
        help="Bulgarian identity card, or the residence document of a "
             "third-country national.")
    l10n_bg_id_card_expiry = fields.Date(
        string='ID Card Expires On', groups='hr.group_hr_user', tracking=True)

    # ⚖️ Закрилата е самостоятелно основание за пребиваване по ЗУБ.
    l10n_bg_protection_status = fields.Selection([
        ('refugee', 'Refugee Status'),
        ('humanitarian', 'Humanitarian Status'),
        ('temporary', 'Temporary Protection'),
        ('other', 'Other Ground'),
    ], string='Protection Status', groups='hr.group_hr_user', tracking=True,
        help="Ground of residence under the Asylum and Refugees Act.")
    l10n_bg_protection_expiry = fields.Date(
        string='Protection Expires On', groups='hr.group_hr_user', tracking=True)

    # Личен лекар
    l10n_bg_personal_doctor = fields.Char(
        string='Personal Doctor', groups='hr.group_hr_user',
        help="General practitioner, as declared by the employee.")
    l10n_bg_personal_doctor_phone = fields.Char(
        string='Doctor Phone', groups='hr.group_hr_user')
    l10n_bg_personal_doctor_address = fields.Char(
        string='Doctor Address', groups='hr.group_hr_user')

    # 🔑 Срокът на ТЕЛК решението е кадрови факт: изтече ли, отпадат и
    # данъчното облекчение, и подът на отпуска по чл. 319 КТ.
    l10n_bg_disability_expiry = fields.Date(
        string='Disability Decision Expires On', groups='hr.group_hr_user',
        tracking=True,
        help="Expiry of the TELK/NELK decision. When it lapses, both the "
             "monthly PIT relief and the Art. 319 LC leave floor stop "
             "applying.")

    # Данъчният номер от друга държава — отделен от `ssnid` (решение на Росен,
    # 04.09.2026). За българските граждани идентификаторът е ЕГН.
    l10n_bg_tax_number = fields.Char(
        string='Foreign Tax Number', groups='hr.group_hr_user', tracking=True,
        help="Tax identification number issued by the state of birth or "
             "citizenship of a foreign employee. Bulgarian citizens are "
             "identified by their EGN in Identification No.")

    # =========================================================================
    # НОВО ОТ 19 — РЕШЕНИЯ НА ТЕЛК/НЕЛК
    # =========================================================================

    l10n_bg_telk_decision_ids = fields.One2many(
        'l10n_bg.telk.decision', 'employee_id',
        string='TELK/NELK Decisions', groups='hr.group_hr_user')
    l10n_bg_telk_decision_count = fields.Integer(
        string='Decisions', compute='_compute_l10n_bg_telk_decision_count',
        groups='hr.group_hr_user')
    l10n_bg_telk_current_id = fields.Many2one(
        'l10n_bg.telk.decision', string='Decision in Force',
        compute='_compute_l10n_bg_telk_current_id', groups='hr.group_hr_user',
        help="The decision in force today. History is kept in full — a new "
             "decision does not overwrite the previous one.")
    l10n_bg_telk_expired = fields.Boolean(
        string='Decision Expired', compute='_compute_l10n_bg_telk_current_id',
        groups='hr.group_hr_user',
        help="There is a decision on file, but none of them is in force today "
             "— which is a different situation from having no decision at all.")

    @api.depends('l10n_bg_telk_decision_ids')
    def _compute_l10n_bg_telk_decision_count(self):
        for employee in self:
            employee.l10n_bg_telk_decision_count = len(
                employee.l10n_bg_telk_decision_ids)

    @api.depends('l10n_bg_telk_decision_ids.date_from',
                 'l10n_bg_telk_decision_ids.date_to')
    def _compute_l10n_bg_telk_current_id(self):
        """🔑 „Няма решение“ и „решението е изтекло“ са РАЗЛИЧНИ положения."""
        Decision = self.env['l10n_bg.telk.decision']
        dnes = fields.Date.context_today(self)
        for employee in self:
            deystvashto = Decision.decision_at(employee, dnes)
            employee.l10n_bg_telk_current_id = deystvashto
            employee.l10n_bg_telk_expired = bool(
                not deystvashto and Decision.latest_for(employee))

    def action_l10n_bg_open_telk_decisions(self):
        """Отваря решенията на този служител — от бутона на формата."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('TELK/NELK Decisions'),
            'res_model': 'l10n_bg.telk.decision',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    # =========================================================================
    # НОВО ОТ 19 — СРОКОВЕТЕ НА ДОКУМЕНТИТЕ: ЕДНО УВЕДОМЛЕНИЕ ЗА ВСИЧКИ
    # =========================================================================

    def _l10n_bg_document_expiries(self):
        """Всички срокове на документи на служителя — [(етикет, дата)].

        Паспортът със срок НЕ е тук: в 18 ядрото няма срок на паспорта.
        """
        self.ensure_one()
        return [
            (_("ID card"), self.l10n_bg_id_card_expiry),
            (_("Protection status"), self.l10n_bg_protection_expiry),
            (_("Work permit"), self.work_permit_expiration_date),
            (_("Visa"), self.visa_expire),
            (_("Disability decision (TELK/NELK)"), self.l10n_bg_disability_expiry),
        ]

    @api.model
    def cron_l10n_bg_notify_expiring_documents(self):
        """Три месеца преди срока: дейност върху служителя, не мейл.

        Дедупликацията е по резюмето: същият документ със същия срок ражда
        ЕДНА отворена дейност; подновен документ = нов срок = ново резюме.
        """
        dnes = fields.Date.today()
        prag = dnes + timedelta(days=self._L10N_BG_DOCUMENT_LEAD_DAYS)
        Activity = self.env['mail.activity'].sudo()
        admin = self.env.ref('base.user_admin', raise_if_not_found=False)
        broi = 0
        for emp in self.sudo().search([('active', '=', True)]):
            for etiket, srok in emp._l10n_bg_document_expiries():
                if not srok or srok < dnes or srok > prag:
                    continue
                rezyume = _("%(doc)s expires on %(date)s", doc=etiket, date=srok)
                if Activity.search_count([
                    ('res_model', '=', 'hr.employee'),
                    ('res_id', '=', emp.id),
                    ('summary', '=', rezyume),
                ]):
                    continue
                otgovornik = (emp.contract_id.hr_responsible_id
                              or admin or self.env.user)
                emp.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    date_deadline=srok,
                    summary=rezyume,
                    note=_("Document expiring in less than %(days)d days: "
                           "%(doc)s, valid until %(date)s. Arrange the renewal "
                           "and update the employee record.",
                           days=self._L10N_BG_DOCUMENT_LEAD_DAYS,
                           doc=etiket, date=srok),
                    user_id=otgovornik.id)
                broi += 1
        if broi:
            _logger.info("Изтичащи документи до %s: %d нови дейности", prag, broi)
        return broi
