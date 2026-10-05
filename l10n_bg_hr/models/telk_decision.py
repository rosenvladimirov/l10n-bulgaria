# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Решенията на ТЕЛК — регистър със СРОК, защото точно срокът изтича.

Пренесено от `l10n_bg_hr` 19.0.2.9.13 (`models/telk_decision.py`). Разлики:
· `models.Constraint` (API на 19) → `_sql_constraints`;
· `_rec_name` е `number` — в 18 `display_name` не става за `_rec_name`.

Имената на полетата и подписите на `decision_at` / `latest_for` НЕ се менят:
същият `_name` живее и в 19, и двата вида трябва да са съвместими.

🔑 Решението не е признак, а ДОКУМЕНТ с начало и край — изтече ли, отпадат и
правата, които висят на него (чл. 319 КТ, облекчението по ЗДДФЛ). Процентът е
ЦЯЛО число с гард: дробта 0.51 вместо 51 минава „има ли намалена
работоспособност“ и пада на „50 и над“.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class L10nBgTelkDecision(models.Model):
    _name = 'l10n_bg.telk.decision'
    _description = 'TELK Decision'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # 🔑 По ДАТА НА ИЗДАВАНЕ, после по началото на срока.
    _order = 'date_decision desc, date_from desc, id desc'
    _rec_name = 'number'

    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='cascade', index=True)
    number = fields.Char(
        required=True, tracking=True,
        help="Decision number as issued.")
    issuing_body = fields.Char(
        help="The TELK or NELK panel that issued the decision.")
    percent = fields.Integer(
        string='Reduced Working Capacity (%)', required=True, tracking=True,
        help="Whole per cent, from 1 to 100 — not a fraction. A decision "
             "recorded as 0.51 instead of 51 passes every 'is there a "
             "disability' test and fails every 'fifty or more' test.")
    date_decision = fields.Date(string='Issued on')
    date_from = fields.Date(
        string='In force from', required=True, index=True, tracking=True)
    date_to = fields.Date(
        string='In force until', tracking=True,
        help="Empty means the decision is for life. Otherwise the rights that "
             "hang on it end with it.")
    diagnosis = fields.Char()
    note = fields.Text()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('number_employee_uniq', 'unique(employee_id, number)',
         'The same decision cannot be recorded twice for one employee.'),
    ]

    @api.depends('number', 'percent', 'date_from', 'date_to')
    def _compute_display_name(self):
        for record in self:
            period = '%s → %s' % (record.date_from or '?',
                                  record.date_to or _('for life'))
            record.display_name = '%s · %s%% · %s' % (
                record.number or '?', record.percent, period)

    @api.constrains('percent')
    def _check_percent_is_whole(self):
        """🚨 Процентът е ЦЯЛО число между 1 и 100 (хваща и нулата)."""
        for record in self:
            if not 1 <= record.percent <= 100:
                raise ValidationError(_(
                    "The reduced working capacity on decision %(number)s is "
                    "%(percent)s. It must be a whole per cent between 1 and "
                    "100 — a fraction such as 0.51 instead of 51 passes every "
                    "'is there a disability' test and fails every 'fifty or "
                    "more' one.",
                    number=record.number or '?', percent=record.percent))

    @api.constrains('date_from', 'date_to')
    def _check_period(self):
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError(_(
                    "Decision %s stops applying before it starts.",
                    record.number or '?'))

    @api.model
    def latest_for(self, employee):
        """Последното решение на лицето, независимо дали още важи.

        🔑 Различава „НЯМА решение“ от „решението е ИЗТЕКЛО“.
        """
        if not employee:
            return self.browse()
        return self.search(
            [('employee_id', '=', employee.id)],
            order='date_decision desc, date_from desc, id desc', limit=1)

    @api.model
    def decision_at(self, employee, date):
        """Решението, което важи за това лице на тази дата (или празно)."""
        if not employee or not date:
            return self.browse()
        return self.search([
            ('employee_id', '=', employee.id),
            ('date_from', '<=', date),
            '|', ('date_to', '=', False), ('date_to', '>=', date),
        ], order='date_from desc', limit=1)
