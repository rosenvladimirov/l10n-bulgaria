# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import SQL


class HrLeaveBalanceYear(models.Model):
    """Leave balance broken down by calendar year (FEAT-5).

    Сестра на `hr.leave.balance`, но с допълнително измерение `year`. Базовият
    модел дава lifetime агрегат per (employee, leave_type); тук разбивката е per
    (employee, leave_type, year), за да се вижда остатъкът по години (КТ чл.176а
    отложен отпуск — клиентът иска да следи остатъци 2023/2024/2025...).

    Намеренно ОТДЕЛЕН модел (а не нова колона в hr.leave.balance), за да не се
    чупи документираната parity на базовия view и неговите downstream hook-ове.

    Година:
    - за allocations → `EXTRACT(YEAR FROM date_from)` (годината на гранта);
    - за taken leaves → `EXTRACT(YEAR FROM request_date_from)` (годината на
      ползване).
    FULL OUTER JOIN по (employee, leave_type, year) — година само с гранти или
    само с ползвания се появява и в двата случая.

    Read-only SQL view (`_auto = False`), същият canonical pattern като
    hr.leave.balance.
    """

    _name = "hr.leave.balance.year"
    _description = "Leave Balance by Year"
    _auto = False
    _order = "employee_id, leave_type_id, year desc"

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", readonly=True)
    company_id = fields.Many2one(
        "res.company", string="Company", readonly=True,
        help="Employee's company — drives the multi-company record rule and "
             "the company-switcher filtering.")
    leave_type_id = fields.Many2one(
        "hr.leave.type", string="Leave Type", readonly=True)
    leave_type_code = fields.Char(
        string="NSSI/KT Code", readonly=True,
        help="БГ-специфичен код от hr.leave.type.l10n_bg_code.")
    year = fields.Integer(
        string="Year", readonly=True,
        help="Календарна година: за гранти от allocation.date_from, за ползвания "
             "от leave.request_date_from.")
    allocated_days = fields.Float(
        string="Allocated Days", readonly=True,
        help="Сума на validated allocations с date_from в тази година.")
    taken_days = fields.Float(
        string="Taken Days", readonly=True,
        help="Сума на validated leaves с request_date_from в тази година.")
    remaining_days = fields.Float(
        string="Remaining Days", readonly=True,
        help="allocated_days − taken_days за годината (информационно — при "
             "пренос остатъкът от дадена година се ползва в следваща).")

    _depends = {
        "hr.leave": [
            "employee_id", "holiday_status_id", "state",
            "number_of_days", "request_date_from",
        ],
        "hr.leave.allocation": [
            "employee_id", "holiday_status_id", "state",
            "number_of_days", "date_from",
        ],
        "hr.leave.type": [
            "l10n_bg_code",
        ],
        "hr.employee": [
            "company_id",
        ],
    }

    @property
    def _table_query(self) -> SQL:
        return SQL("%s %s", self._select(), self._from())

    @api.model
    def _select(self) -> SQL:
        return SQL("""
            SELECT
                ROW_NUMBER() OVER (
                    ORDER BY employee_id, holiday_status_id, year
                ) AS id,
                employee_id AS employee_id,
                emp.company_id AS company_id,
                holiday_status_id AS leave_type_id,
                lt.l10n_bg_code AS leave_type_code,
                year AS year,
                COALESCE(allocated.days, 0) AS allocated_days,
                COALESCE(taken.days_validated, 0) AS taken_days,
                COALESCE(allocated.days, 0) - COALESCE(taken.days_validated, 0)
                    AS remaining_days
        """)

    @api.model
    def _from(self) -> SQL:
        return SQL(
            "FROM (%s) AS allocated "
            "FULL OUTER JOIN (%s) AS taken "
            "    USING (employee_id, holiday_status_id, year) "
            "LEFT JOIN hr_leave_type lt ON lt.id = holiday_status_id "
            "LEFT JOIN hr_employee emp ON emp.id = employee_id",
            self._allocated_subquery(),
            self._taken_subquery(),
        )

    @api.model
    def _allocated_subquery(self) -> SQL:
        """Validated allocations групирани по година на date_from."""
        return SQL("""
            SELECT
                employee_id,
                holiday_status_id,
                EXTRACT(YEAR FROM date_from)::int AS year,
                SUM(number_of_days) AS days
            FROM hr_leave_allocation
            WHERE state = 'validate'
              AND date_from IS NOT NULL
            GROUP BY employee_id, holiday_status_id, EXTRACT(YEAR FROM date_from)
        """)

    @api.model
    def _taken_subquery(self) -> SQL:
        """Validated leaves групирани по година на request_date_from."""
        return SQL("""
            SELECT
                employee_id,
                holiday_status_id,
                EXTRACT(YEAR FROM request_date_from)::int AS year,
                SUM(CASE WHEN state = 'validate'
                    THEN number_of_days ELSE 0 END) AS days_validated
            FROM hr_leave
            WHERE state IN ('validate', 'confirm', 'validate1')
              AND request_date_from IS NOT NULL
            GROUP BY employee_id, holiday_status_id,
                     EXTRACT(YEAR FROM request_date_from)
        """)
