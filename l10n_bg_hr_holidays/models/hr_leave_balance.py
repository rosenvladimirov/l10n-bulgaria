# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import SQL


class HrLeaveBalance(models.Model):
    """Leave balance read-only view.

    Aggregates `hr.leave.allocation` records against `hr.leave` records per
    (employee, leave_type) to expose allocated / taken / remaining days.

    **Canonical parity (2026-05-21)**: numbers за регулярни allocations
    съответстват на резултата от `hr.work.entry.type.get_allocation_data()` —
    canonical Odoo API. Двата източника бяха сравнени и за тестов случай
    Платен Отпуск 22 alloc / 4 taken / 18 remaining → стойностите съвпадат.

    **Разлика с canonical API**:
    - SQL view-ът е „lifetime" агрегат (без date filter) — подходящо за
      типове без accrual.
    - При accrual plans canonical-ът смята `_get_future_leaves_on(target_date)`
      на ниво allocation — тук тази проекция липсва. За acrrual leave types
      override `_allocated_subquery()` в кастъм модул.
    - Canonical разделя `leaves_taken` (state=validate) от `virtual_leaves_taken`
      (вкл. confirm/validate1) — този view сега експонира двете отделно
      през `taken_days` (validate) и `virtual_taken_days` (+pending).

    Built as PostgreSQL view през canonical Odoo SQL-report pattern (виж
    `addons/account/report/account_invoice_report.py`):
    - `_auto = False` — read-only.
    - `_table_query` @property — replaces legacy init() + CREATE VIEW.
    - `_depends` dict — declarative cache invalidation.
    - Hook методи (`_select()` / `_from()` / `_allocated_subquery()` /
      `_taken_subquery()`) — overridable за scope-ване (per year), допълнителни
      колони (БГ NSSI codes), специфични филтри. Виж примерно
      `l10n_bg_hr_payroll` за accrual scoping.

    **БГ extensions** (l10n_bg_hr_payroll, l10n_bg_hr_payroll_*):
    - `leave_type_code` (NSSI код от work_entry_type_id.l10n_bg_code) — за
      групиране по медицински категории (01-03/08-09 illness, 04 maternity,
      05-07 family care).
    - Future: separate `sick_taken_*`, `maternity_taken_*` агрегати — ще
      бъдат добавени директно в този view през `_extra_select()` hook.
    """

    _name = "hr.leave.balance"
    _description = "Leave Balance"
    _auto = False
    _order = "employee_id, leave_type_id"

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", readonly=True)
    company_id = fields.Many2one(
        "res.company", string="Company", readonly=True,
        help="Employee's company — drives the multi-company record rule and "
             "the company-switcher filtering.")
    leave_type_id = fields.Many2one(
        "hr.work.entry.type", string="Leave Type", readonly=True)
    leave_type_code = fields.Char(
        string="NSSI/KT Code", readonly=True,
        help="БГ-специфичен код от hr.work.entry.type.l10n_bg_code (01-17 НОИ + KT*). "
             "За групиране по медицински категории в downstream агрегати.")
    unit_of_measure = fields.Char(
        string="Request Unit", readonly=True,
        help="day / half_day / hour — за конверсия в канонични дни.")
    allocated_days = fields.Float(
        string="Allocated Days", readonly=True,
        help="Сума на всички validated allocations (lifetime).")
    taken_days = fields.Float(
        string="Taken Days", readonly=True,
        help="Сума на validated leaves (state='validate').")
    virtual_taken_days = fields.Float(
        string="Virtual Taken Days", readonly=True,
        help="Taken + pending (state IN ('confirm', 'validate1', 'validate')). "
             "Парира virtual_leaves_taken в hr.work.entry.type.get_allocation_data.")
    remaining_days = fields.Float(
        string="Remaining Days", readonly=True,
        help="allocated_days − taken_days (без pending заявки).")
    virtual_remaining_days = fields.Float(
        string="Virtual Remaining Days", readonly=True,
        help="allocated_days − virtual_taken_days. Парира virtual_remaining_leaves "
             "в canonical get_allocation_data — реалният 'свободен' остатък след "
             "като се изчистят заявените, но още неодобрени дни.")

    _depends = {
        "hr.leave": [
            "employee_id", "work_entry_type_id", "state",
            "number_of_days", "request_date_from",
        ],
        "hr.leave.allocation": [
            "employee_id", "work_entry_type_id", "state",
            "number_of_days", "date_from", "date_to",
        ],
        "hr.work.entry.type": [
            "l10n_bg_code", "unit_of_measure",
        ],
        "hr.employee": [
            "company_id",
        ],
    }

    @property
    def _table_query(self) -> SQL:
        return SQL("%s %s", self._select(), self._from())

    def init(self):
        """Explicit (re)creation of the SQL view.

        Odoo's automatic `_table_query` view management is unreliable across
        installs/upgrades (it refuses to recreate an existing view — logs
        "disabling automatic schema management" — and a column-set change can
        otherwise break a CREATE OR REPLACE). DROP + CREATE here guarantees the
        view always matches the current `_select()`/`_from()`, on both `-i` and
        `-u`. Runtime-verified 2026-06-09 (виж payroll-trackers gate).
        """
        self.env.cr.execute(SQL(
            "DROP VIEW IF EXISTS %s CASCADE", SQL.identifier(self._table)))
        self.env.cr.execute(SQL(
            "CREATE VIEW %s AS (%s)",
            SQL.identifier(self._table), self._table_query))

    @api.model
    def _select(self) -> SQL:
        return SQL("""
            SELECT
                ROW_NUMBER() OVER (
                    ORDER BY allocated.employee_id, allocated.work_entry_type_id
                ) AS id,
                allocated.employee_id AS employee_id,
                emp.company_id AS company_id,
                allocated.work_entry_type_id AS leave_type_id,
                lt.l10n_bg_code AS leave_type_code,
                lt.unit_of_measure AS unit_of_measure,
                allocated.days AS allocated_days,
                COALESCE(taken.days_validated, 0) AS taken_days,
                COALESCE(taken.days_pending, 0) + COALESCE(taken.days_validated, 0)
                    AS virtual_taken_days,
                allocated.days - COALESCE(taken.days_validated, 0)
                    AS remaining_days,
                allocated.days
                    - COALESCE(taken.days_validated, 0)
                    - COALESCE(taken.days_pending, 0)
                    AS virtual_remaining_days
        """)

    @api.model
    def _from(self) -> SQL:
        return SQL(
            "FROM (%s) AS allocated "
            "LEFT JOIN (%s) AS taken USING (employee_id, work_entry_type_id) "
            "LEFT JOIN hr_work_entry_type lt ON lt.id = allocated.work_entry_type_id "
            "LEFT JOIN hr_employee emp ON emp.id = allocated.employee_id",
            self._allocated_subquery(),
            self._taken_subquery(),
        )

    @api.model
    def _allocated_subquery(self) -> SQL:
        """Pre-aggregated allocations, валидни КЪМ ДНЕС.

        Парира canonical поведение: брои само allocations където днешната
        дата е в интервала [date_from, date_to]. Изтекли алокации (date_to
        в миналото) и бъдещи (date_from в бъдещето) се пропускат — те не
        формират current балансаз.

        Канонично референция: addons/hr_holidays/models/hr_leave_allocation.py
        _get_allocation_data_request → филтрира по същия начин преди да
        пресметне max_leaves.

        Override в downstream module за специфично scope-ване (напр. per
        година ако trябва lifetime view, или за accrual proration).
        """
        return SQL("""
            SELECT employee_id, work_entry_type_id, SUM(number_of_days) AS days
            FROM hr_leave_allocation
            WHERE state = 'validate'
              AND (date_from IS NULL OR date_from <= CURRENT_DATE)
              AND (date_to   IS NULL OR date_to   >= CURRENT_DATE)
            GROUP BY employee_id, work_entry_type_id
        """)

    @api.model
    def _taken_subquery(self) -> SQL:
        """Pre-aggregated taken leaves, до ДНЕШНА ДАТА.

        Критичен филтър: request_date_from <= CURRENT_DATE. Без този филтър
        SQL view-ът броеше бъдещи планирани отпуски като „ползвани", което
        правеше virtual_remaining_days негативно при служители с одобрени
        отпуски напред в годината. Сега се парира canonical
        get_allocation_data(employee, today) поведението — таken
        отразява само случилия се труд.

        Разделение:
        - days_validated → leaves_taken (state='validate')
        - days_pending → разлика до virtual_leaves_taken (confirm + validate1)

        Refuse / cancel state-овете се изключват.

        За проекция към края на годината — използвай canonical
        leave_type.get_allocation_data(employee, end_of_year) на ниво
        контролер (виж l10n_bg_hr_portal dashboard).
        """
        return SQL("""
            SELECT
                employee_id,
                work_entry_type_id,
                SUM(CASE WHEN state = 'validate'
                    THEN number_of_days ELSE 0 END) AS days_validated,
                SUM(CASE WHEN state IN ('confirm', 'validate1')
                    THEN number_of_days ELSE 0 END) AS days_pending
            FROM hr_leave
            WHERE state IN ('validate', 'confirm', 'validate1')
              AND request_date_from <= CURRENT_DATE
            GROUP BY employee_id, work_entry_type_id
        """)
