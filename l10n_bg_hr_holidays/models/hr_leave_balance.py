# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import SQL


class HrLeaveBalance(models.Model):
    """Leave balance read-only view.

    Aggregates validated `hr.leave.allocation` records against validated
    `hr.leave` records per (employee, leave_type) to expose allocated /
    taken / remaining days. Built as a PostgreSQL view via the canonical
    Odoo 19 SQL-report pattern (see `addons/account/report/account_invoice_report.py`,
    `addons/sale/report/sale_report.py`):

    * `_auto = False` — model is read-only.
    * `_table_query` @property — replaces legacy `init()` + `CREATE VIEW`.
    * `_depends` dict — declarative cache invalidation.
    * `_select()` / `_from()` / `_allocated_subquery()` / `_taken_subquery()`
      hook methods returning `odoo.tools.SQL` instances — overridable by
      downstream modules to scope (e.g. by year), filter or extend columns.

    The aggregation is **lifetime** — historical allocations and leaves
    are summed without a date filter. For non-accrual leave types (military,
    maternity, etc.) this is the intended balance. For accrual-type leave
    types that reset annually (annual paid leave), override
    `_allocated_subquery()` to scope by current period in a custom module.

    Replaces a previously manual `x_leave_balance` workaround installed
    directly on customer databases.
    """

    _name = "hr.leave.balance"
    _description = "Leave Balance"
    _auto = False
    _order = "employee_id, leave_type_id"

    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    leave_type_id = fields.Many2one("hr.leave.type", string="Leave Type", readonly=True)
    allocated_days = fields.Float(string="Allocated Days", readonly=True)
    taken_days = fields.Float(string="Taken Days", readonly=True)
    remaining_days = fields.Float(string="Remaining Days", readonly=True)

    _depends = {
        'hr.leave': ['employee_id', 'holiday_status_id', 'state', 'number_of_days'],
        'hr.leave.allocation': ['employee_id', 'holiday_status_id', 'state', 'number_of_days'],
    }

    @property
    def _table_query(self) -> SQL:
        return SQL("%s %s", self._select(), self._from())

    @api.model
    def _select(self) -> SQL:
        return SQL("""
            SELECT
                ROW_NUMBER() OVER (
                    ORDER BY allocated.employee_id, allocated.holiday_status_id
                ) AS id,
                allocated.employee_id AS employee_id,
                allocated.holiday_status_id AS leave_type_id,
                allocated.days AS allocated_days,
                COALESCE(taken.days, 0) AS taken_days,
                allocated.days - COALESCE(taken.days, 0) AS remaining_days
        """)

    @api.model
    def _from(self) -> SQL:
        return SQL(
            "FROM (%s) AS allocated LEFT JOIN (%s) AS taken USING (employee_id, holiday_status_id)",
            self._allocated_subquery(),
            self._taken_subquery(),
        )

    @api.model
    def _allocated_subquery(self) -> SQL:
        """Pre-aggregated allocations. Override to scope (e.g. by year)."""
        return SQL("""
            SELECT employee_id, holiday_status_id, SUM(number_of_days) AS days
            FROM hr_leave_allocation
            WHERE state = 'validate'
            GROUP BY employee_id, holiday_status_id
        """)

    @api.model
    def _taken_subquery(self) -> SQL:
        """Pre-aggregated taken leaves. Override to scope (e.g. by year)."""
        return SQL("""
            SELECT employee_id, holiday_status_id, SUM(number_of_days) AS days
            FROM hr_leave
            WHERE state = 'validate'
            GROUP BY employee_id, holiday_status_id
        """)
