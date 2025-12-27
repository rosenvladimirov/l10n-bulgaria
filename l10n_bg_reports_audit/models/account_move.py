from odoo import api, fields, models

from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    get_delivery_type,
    get_doc_type,
    get_type_vat,
)


class AccountMove(models.Model):
    _inherit = "account.move"

    # Ново поле
    l10n_bg_type_vat = fields.Selection(
        selection=get_type_vat(),
        string="Type of numbering",
        default="standard",
        copy=False,
        index=True,
    )

    l10n_bg_narration = fields.Char(
        string="Narration for audit report",
        translate=True,
        copy=False,
    )

    # Override на l10n_bg_exemption_reason с разширен selection
    l10n_bg_exemption_reason = fields.Selection(
        selection=get_delivery_type(),
        string="Exemption reason (BG)",
    )

    # Related полета за обратна съвместимост
    l10n_bg_doc_type = fields.Selection(
        related='l10n_bg_document_type',
        string="VAT type document",
        store=True,
        readonly=False,
    )
    l10n_bg_delivery_type = fields.Selection(
        related='l10n_bg_exemption_reason',
        string="VAT type delivery",
        store=True,
        readonly=False,
    )

    # Override на selection метода за l10n_bg_document_type
    def _l10n_bg_document_type_selection_values(self):
        """Override: Разширен списък с типове документи"""
        return get_doc_type()
