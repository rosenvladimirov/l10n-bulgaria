# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = ["hr.employee.public", "res.transliterate.mixin"]
    _name = "hr.employee.public"

    name = fields.Char(translate=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS hr_employee_public CASCADE")
        return super().init()
