#  Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Минималният осигурителен доход, датиран.

🚨 Защо отделен модел, а не втори запис на дейността.

Дейността смесваше две неща в един ред: КОЙ е КИД кодът (идентичност, вечна) и
КОЛКО е МОД-ът (стойност, периодична). Затова `date_from`/`date_to` на самата
дейност не вършеха работа и стояха неползвани — четат се само от `_check_dates`
и от изгледите, нула употреби в изчислителния път.

Разцепването на дейността по период е пробвано и **оттеглено**:
`l10n_bg_2026_classifications` стои с `installable: False`. Трите механизма,
които го убиват, важат и за всеки бъдещ опит:

  1. `hr.version.l10n_bg_economic_activity_id` е Many2one към ЕДИН запис.
     Клонираш ли дейността, заварените версии продължават да сочат стария ред
     и августовският фиш взима януарски праг — мълчаливо, точно дефектът,
     който гоним.
  2. Д1 поле 12 чете `.code` от същия Many2one. Два записа с еднакъв код
     правят падащото меню двусмислено за ТРЗ.
  3. Йерархията `parent_id` се обхожда нагоре; клонирането я удвоява.

⇒ Идентичността остава ЕДИН запис; сумите слизат в датиран ред-дете. Това е
точно шаблонът на `hr.rule.parameter.value`, който вече работи в стека —
`date_to` не е нужен, следващият ред затваря предишния.
"""
from odoo import models, fields, api
from odoo.exceptions import ValidationError

# Групите, по които се води МОД. Огледало на `qualification_group` в
# `bg.hr.payroll.ncop.classification` — нарочно същите ключове, за да няма
# междинен мапинг, който да дрейфне.
#
# ⚠️ `military` (НКПД клас 0 — въоръжени сили) присъства за пълнота, но за него
# МОД НЕ СЕ ПРИЛАГА: в таблицата на НАП `VT23`, колона `C121='0'` няма нито една
# ненулева стойност в нито един период. Липсата на ред е верният отговор, не
# ред с нула.
MOD_GROUPS = [
    ('military', 'Armed Forces'),
    ('manager', 'Managers'),
    ('specialist', 'Specialists'),
    ('technician', 'Technicians'),
    ('clerk', 'Clerks'),
    ('service', 'Service Workers'),
    ('skilled', 'Skilled Workers'),
    ('operator', 'Machine Operators'),
    ('elementary', 'Elementary Occupations'),
]


class BGModValue(models.Model):
    """Една сума на (дейност, квалификационна група, период)."""

    _name = 'bg.hr.payroll.mod.value'
    _description = 'MSSI amount per activity, qualification group and period'
    _order = 'activity_id, qualification_group, date_from desc, id desc'

    activity_id = fields.Many2one(
        'bg.hr.payroll.economic.activity', string='Economic Activity',
        required=True, ondelete='cascade', index=True)
    qualification_group = fields.Selection(
        MOD_GROUPS, string='Qualification Group', required=True, index=True)
    date_from = fields.Date(
        string='Valid From', required=True, index=True,
        help='First day on which this amount applies. The next record for the '
             'same activity and group closes this one.')
    amount = fields.Float(
        string='MSSI Amount', required=True, digits=(12, 2),
        help='Minimum social security income for this activity, qualification '
             'group and period.')
    source = fields.Char(
        string='Source',
        help='Where the amount came from — e.g. the NRA period table it was '
             'built from. Kept so a later reader can tell measured data from '
             'hand-entered.')

    _unique_value = models.Constraint(
        'UNIQUE(activity_id, qualification_group, date_from)',
        'Има вече стойност за тази дейност, група и начална дата.')

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount < 0:
                raise ValidationError(
                    'Минималният осигурителен доход не може да е отрицателен '
                    '(%s, %s).' % (rec.activity_id.display_name,
                                   rec.qualification_group))

    @api.model
    def _l10n_bg_amount_at(self, activity, qualification_group, date):
        """Сумата, в сила на ``date`` — или ``None``, ако няма ред.

        🔑 ``None`` и ``0.0`` значат РАЗЛИЧНИ неща и това е нарочно:

          · няма ред        → „тук не е казано нищо" ⇒ повикващият продължава
                              нагоре по йерархията на КИД;
          · ред с ``0.0``   → „тук ИЗРИЧНО няма праг" ⇒ обхождането СПИРА.

        Днешният код не може да изрази второто, защото чете плоско поле, а
        нулата в него значи „наследи нагоре". Августовската таблица иска точно
        разграничението: има дейности, за които прагът отпада, а родителят им
        носи стойност.
        """
        if not activity or not qualification_group or not date:
            return None
        row = self.search([
            ('activity_id', '=', activity.id),
            ('qualification_group', '=', qualification_group),
            ('date_from', '<=', date),
        ], order='date_from desc, id desc', limit=1)
        return row.amount if row else None
