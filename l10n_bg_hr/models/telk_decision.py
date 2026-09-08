# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Решенията на ТЕЛК — регистър със СРОК, защото точно срокът изтича.

🔑 Решението не е признак, а ДОКУМЕНТ с начало и край. Флаг „има намалена
работоспособност" не може да изтече; решение може — и когато изтече, отпадат и
правата, които виси на него: удълженият отпуск по чл. 319 КТ и данъчното
облекчение по ЗДДФЛ.

🚨 Полигруп го показа отблизо: там стоеше булев флаг и няколко процента, записани
като ДРОБИ (`0.51` вместо `51`) — стойност, която минава през „има ли намалена
работоспособност" и се проваля на „50 и над". Процентът тук е цяло число и има
гард.

⚖️ Регистърът НЕ е нов документооборот. Самите файлове живеят в `documents`
(Odoo EE, вече инсталиран), който сочи към кой да е запис през `res_model` и
`res_id`. Тук стои това, което ТЕЛК решението ЗНАЧИ — процент, срок, орган — а
сканът се закача там.

🔄 ПРЕНЕСЕН от `l10n_bg_version` (дървото `-v20`) на 08.09.2026, ДОСЛОВНО.
Там моделът вече съществуваше и работеше; Полигруп и Конекс обаче въртят
каноничния слой, където го нямаше — затова живее и тук. Двете дървета са с
независима история, тъй че промяна в едното се пренася в другото на ръка:
имената на полетата и подписите на `decision_at` / `latest_for` НЕ се менят
самоволно, инак един и същ `_name` получава два несъвместими вида.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class L10nBgTelkDecision(models.Model):
    _name = 'l10n_bg.telk.decision'
    _description = 'TELK Decision'
    _order = 'date_from desc, id desc'
    _rec_name = 'display_name'

    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='cascade', index=True)
    number = fields.Char(required=True, help="Decision number as issued.")
    issuing_body = fields.Char(
        help="The TELK or NELK panel that issued the decision.")
    percent = fields.Integer(
        string='Reduced Working Capacity (%)', required=True,
        help="Whole per cent, from 1 to 100 — not a fraction. A decision "
             "recorded as 0.51 instead of 51 passes every 'is there a "
             "disability' test and fails every 'fifty or more' test.")
    date_decision = fields.Date(string='Issued on')
    date_from = fields.Date(string='In force from', required=True, index=True)
    date_to = fields.Date(
        string='In force until',
        help="Empty means the decision is for life. Otherwise the rights that "
             "hang on it end with it.")
    diagnosis = fields.Char()
    note = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _number_employee_uniq = models.Constraint(
        'unique(employee_id, number)',
        'The same decision cannot be recorded twice for one employee.')

    @api.depends('number', 'percent', 'date_from', 'date_to')
    def _compute_display_name(self):
        for record in self:
            period = '%s → %s' % (record.date_from or '?',
                                  record.date_to or _('for life'))
            record.display_name = '%s · %s%% · %s' % (
                record.number or '?', record.percent, period)

    @api.constrains('percent')
    def _check_percent_is_whole(self):
        """🚨 Процентът е ЦЯЛО число между 1 и 100.

        Полето е Integer, тъй че дроб не може да влезе оттук — но може да влезе
        от импорт или от миграция на стара база, където е бил Float. Гардът
        хваща и нулата: решение с нула процента не е решение.
        """
        for record in self:
            if not 1 <= record.percent <= 100:
                raise ValidationError(_(
                    "The reduced working capacity on decision %(number)s is "
                    "%(percent)s. It must be a whole per cent between 1 and "
                    "100 — a fraction such as 0.51 instead of 51 passes every "
                    "'is there a disability' test and fails every 'fifty or "
                    "more' one."
                ) % {'number': record.number or '?', 'percent': record.percent})

    @api.constrains('date_from', 'date_to')
    def _check_period(self):
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError(_(
                    "Decision %s stops applying before it starts.")
                    % (record.number or '?'))

    @api.model
    def latest_for(self, employee):
        """Последното решение на лицето, независимо дали още важи.

        🔑 Нужно е, за да се различи „НЯМА решение" от „решението е ИЗТЕКЛО".
        `decision_at` връща само действащото, тъй че изтеклото изглежда точно
        като липсващо — а това са две различни положения: едното иска да се
        подаде документ, другото иска да се преосвидетелства.
        """
        if not employee:
            return self.browse()
        return self.search(
            [('employee_id', '=', employee.id)],
            order='date_from desc, id desc', limit=1)

    @api.model
    def decision_at(self, employee, date):
        """Решението, което важи за това лице на тази дата.

        Връща празен recordset при липса — „няма решение" е легитимен отговор и
        трябва да се различава от „нула процента".
        """
        if not employee or not date:
            return self.browse()
        return self.search([
            ('employee_id', '=', employee.id),
            ('date_from', '<=', date),
            '|', ('date_to', '=', False), ('date_to', '>=', date),
        ], order='date_from desc', limit=1)
