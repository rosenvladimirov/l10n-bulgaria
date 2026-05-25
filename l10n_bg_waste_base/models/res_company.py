# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""res.company разширение: отговорник по отпадъци (за нотификации над квота)."""
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    waste_manager_id = fields.Many2one(
        "res.users",
        string="Waste Manager",
        help="User responsible for waste compliance at the company level. "
             "Receives activities and notifications when a treatment quota "
             "approaches or exceeds the permitted limit.",
    )
