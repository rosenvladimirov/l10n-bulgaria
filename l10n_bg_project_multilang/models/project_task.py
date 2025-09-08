# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    partner_name = fields.Char(
        string='Customer Name',
        translate=True  # Това прави полето многоезично
    )

    partner_company_name = fields.Char(
        string='Customer Company',
        translate=True  # Това прави полето многоезично
    )

