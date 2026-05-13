from odoo import fields, models, tools


class HrLeaveBalance(models.Model):
    _name = "hr.leave.balance"
    _description = "Leave Balance"
    _auto = False
    _order = "employee_id, leave_type_id"

    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    leave_type_id = fields.Many2one("hr.leave.type", string="Leave Type", readonly=True)
    allocated_days = fields.Float(string="Allocated Days", readonly=True)
    taken_days = fields.Float(string="Taken Days", readonly=True)
    remaining_days = fields.Float(string="Remaining Days", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY a.employee_id, a.holiday_status_id) AS id,
                    a.employee_id AS employee_id,
                    a.holiday_status_id AS leave_type_id,
                    SUM(a.number_of_days) AS allocated_days,
                    COALESCE((
                        SELECT SUM(l.number_of_days)
                        FROM hr_leave l
                        WHERE l.employee_id = a.employee_id
                          AND l.holiday_status_id = a.holiday_status_id
                          AND l.state = 'validate'
                    ), 0) AS taken_days,
                    SUM(a.number_of_days) - COALESCE((
                        SELECT SUM(l.number_of_days)
                        FROM hr_leave l
                        WHERE l.employee_id = a.employee_id
                          AND l.holiday_status_id = a.holiday_status_id
                          AND l.state = 'validate'
                    ), 0) AS remaining_days
                FROM hr_leave_allocation a
                WHERE a.state = 'validate'
                GROUP BY a.employee_id, a.holiday_status_id
            )
        """ % self._table)
