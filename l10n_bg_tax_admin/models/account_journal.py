#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    invoice_reference_model = fields.Selection(
        selection_add=[("bg", "Bulgaria")],
        ondelete={"bg": lambda recs: recs.write({"invoice_reference_model": "odoo"})},
    )
    decade = fields.Integer(string="Decade")
