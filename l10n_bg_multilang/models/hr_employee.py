#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeePrivate(models.Model):
    _inherit = ["hr.employee", "res.transliterate.mixin"]
    _name = "hr.employee"

    name = fields.Char(translate=True)
