#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    get_delivery_type,
    get_doc_type,
    get_type_vat,
)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_bg_type_vat = fields.Selection(
        selection=get_type_vat(),
        string="Type of numbering",
        default="standard",
        copy=False,
        index=True,
    )
    l10n_bg_doc_type = fields.Selection(
        selection=get_doc_type(), string="Vat type document", default="01", copy=False
    )
    l10n_bg_delivery_type = fields.Selection(
        selection=get_delivery_type(), string="Vat type delivery", copy=False
    )
    l10n_bg_narration = fields.Char(
        "Narration for audit report", translate=True, copy=False
    )
