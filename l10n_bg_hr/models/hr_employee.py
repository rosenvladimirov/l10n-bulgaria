# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # НКПД / КИД (related from current version)
    l10n_bg_qualification_group = fields.Many2one(
        related='version_id.l10n_bg_qualification_group',
        inherited=True,
        readonly=False,
        groups="hr.group_hr_user",
    )
    l10n_bg_economic_activity_id = fields.Many2one(
        related='version_id.l10n_bg_economic_activity_id',
        inherited=True,
        readonly=False,
        groups="hr.group_hr_user",
    )
    l10n_bg_economic_activity_code = fields.Char(
        related='version_id.l10n_bg_economic_activity_code',
        inherited=True,
        groups="hr.group_hr_user",
    )
    l10n_bg_workplace_code = fields.Char(
        related='version_id.l10n_bg_workplace_code',
        inherited=True,
        readonly=False,
        groups="hr.group_hr_user",
    )

    # =========================================================================
    # СТЕПЕНИ НА ОБРАЗОВАНИЕ ПО БЪЛГАРСКОТО ЗАКОНОДАТЕЛСТВО
    # =========================================================================
    #
    # ⚖️ Ядреното `certificate` предлага graduate / bachelor / master / doctor /
    # other — англосаксонската стълбица. Липсват основното и средното, а точно
    # те са степените по чл. 24, ал. 1 ЗПУО, и точно тях иска ТРЗ (заявка
    # Полигруп, 28.08.2026: „Ниво на сертификат → Диплома; да се добави
    # Основно / Средно").
    #
    # Стълбицата тук е нормативна, не клиентска:
    #   ЗПУО чл. 24, ал. 1 — степените на училищното образование са ОСНОВНО и
    #   СРЕДНО. „Начално" е ЕТАП по чл. 25, не степен, но ТРЗ го записва, тъй че
    #   присъства с изрична бележка.
    #   ЗВО чл. 42, ал. 1 — образователно-квалификационните степени са
    #   „професионален бакалавър по …", „бакалавър" и „магистър"; т. 3 добавя
    #   образователната и научна степен „доктор".
    #
    # 🚨 Ядрените ключове НЕ се пипат. `graduate` и `other` остават: по тях има
    # данни в заварените бази и смяната на ключ би ги обезсмислила мълчаливо.
    # Затова се ДОБАВЯ, не се замества.

    @api.model
    def _get_certificate_selection(self):
        """Българската стълбица, подредена от най-ниската степен към най-високата.

        Редът има значение: падащото меню се чете отгоре надолу и ТРЗ избира по
        възходящ ред, не по азбучен.
        """
        yadro = dict(super()._get_certificate_selection())
        stalbica = [
            ('l10n_bg_none', self.env._('No formal education')),
            # Етап по чл. 25 ЗПУО, не степен — но се записва в практиката.
            ('l10n_bg_primary', self.env._('Primary (Grades I-IV)')),
            ('l10n_bg_basic', self.env._('Basic education (Art. 24 (1) 1 PSEA)')),
            ('l10n_bg_secondary', self.env._('Secondary education (Art. 24 (1) 2 PSEA)')),
            ('l10n_bg_vocational_bachelor',
             self.env._('Professional Bachelor (Art. 42 (1) 1 HEA)')),
            ('bachelor', yadro.get('bachelor', self.env._('Bachelor'))),
            ('master', yadro.get('master', self.env._('Master'))),
            ('doctor', yadro.get('doctor', self.env._('Doctor'))),
            ('l10n_bg_doctor_of_science', self.env._('Doctor of Sciences')),
        ]
        # Заварените ключове, които стълбицата не покрива — на края, за да не
        # изчезнат стойности от заварени записи.
        pokriti = {k for k, _v in stalbica}
        ostatak = [(k, v) for k, v in super()._get_certificate_selection()
                   if k not in pokriti]
        return stalbica + ostatak

    def action_refresh_nkpd_kid(self):
        """Refresh НКПД and КИД from current job position."""
        for employee in self:
            version = employee.version_id
            if not version:
                continue
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

    l10n_bg_amendment_ids = fields.One2many(
        'l10n_bg.hr.version.amendment',
        'employee_id',
        string='Contract Amendments',
    )

    l10n_bg_amendment_count = fields.Integer(
        string='Amendment Count',
        compute='_compute_amendment_count',
    )

    l10n_bg_last_amendment_date = fields.Date(
        string='Last Amendment Date',
        compute='_compute_last_amendment',
    )

    l10n_bg_last_amendment_summary = fields.Char(
        string='Last Amendment Changes',
        compute='_compute_last_amendment',
    )

    @api.depends('l10n_bg_amendment_ids')
    def _compute_amendment_count(self):
        for employee in self:
            employee.l10n_bg_amendment_count = len(employee.l10n_bg_amendment_ids)

    @api.depends('l10n_bg_amendment_ids.state', 'l10n_bg_amendment_ids.date_effective')
    def _compute_last_amendment(self):
        for employee in self:
            last = employee.l10n_bg_amendment_ids.filtered(
                lambda a: a.state in ('active', 'approved', 'to_approve')
            ).sorted('date_effective', reverse=True)[:1]
            employee.l10n_bg_last_amendment_date = last.date_effective if last else False
            employee.l10n_bg_last_amendment_summary = last.get_amendment_summary() if last else ''

    # =========================================================================
    # РЕШЕНИЯ НА ТЕЛК/НЕЛК
    # =========================================================================
    #
    # Моделът е пренесен от `-v20` (виж `telk_decision.py`). Тук стоят само
    # връзката и бързият достъп; резолвирането по дата НЕ се преписва —
    # ползва се `decision_at` / `latest_for` на самия модел, за да има ЕДИН
    # отговор на въпроса „кое решение важи".

    l10n_bg_telk_decision_ids = fields.One2many(
        'l10n_bg.telk.decision', 'employee_id',
        string='TELK/NELK Decisions', groups='hr.group_hr_user')
    l10n_bg_telk_decision_count = fields.Integer(
        string='Decisions', compute='_compute_l10n_bg_telk_decision_count')
    l10n_bg_telk_current_id = fields.Many2one(
        'l10n_bg.telk.decision', string='Decision in Force',
        compute='_compute_l10n_bg_telk_current_id', groups='hr.group_hr_user',
        help="The decision in force today. History is kept in full — a new "
             "decision does not overwrite the previous one.")
    l10n_bg_telk_expired = fields.Boolean(
        string='Decision Expired', compute='_compute_l10n_bg_telk_current_id',
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
        """🔑 „Няма решение" и „решението е изтекло" са РАЗЛИЧНИ положения.

        Първото иска да се подаде документ, второто — преосвидетелстване.
        Затова се четат и двата метода на модела, не само действащото.
        """
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
