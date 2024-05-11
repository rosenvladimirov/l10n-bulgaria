#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class TAXForms(models.Model):
    _inherit = "tax.forms"

    account_forms = fields.Selection(
        selection_add=[
            ("vat_purchase", _("VAT Purchase journal")),
            ("vat_sale", _("VAT Sale journal")),
            ("vat_vies", _("VIES Declaration")),
        ],
        ondelete={
            "vat_purchase": "set default",
            "vat_sale": "set default",
            "vat_vies": "set default",
        },
    )
