#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools

from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    get_delivery_type,
    get_doc_type,
    get_type_vat,
)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_bg_customs_base_amount = fields.Float(
        string="Customs base amount",
        help="Customs base amount used in audit reports.",
    )
    l10n_bg_audit_use_tax = fields.Boolean(
        related="company_id.l10n_bg_audit_use_tax",
        readonly=True,
    )

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
    l10n_bg_tax_tag_id = fields.Many2one(
        comodel_name="account.account.tag",
        string="BG tax tag",
        help=(
            "Additional tax tag to apply on tax lines when the tax group has "
            "payable/receivable accounts set."
        ),
    )

    # Override на selection метода за l10n_bg_document_type
    def _l10n_bg_document_type_selection_values(self):
        """Override: Разширен списък с типове документи"""
        return get_doc_type()

    def write(self, vals):
        track_tag = 'l10n_bg_tax_tag_id' in vals
        old_tags = {}
        if track_tag:
            for move in self:
                old_tags[move.id] = move.l10n_bg_tax_tag_id
        res = super().write(vals)
        if track_tag:
            for move in self:
                old_tag = old_tags.get(move.id)
                new_tag = move.l10n_bg_tax_tag_id
                if track_tag and old_tag and old_tag != new_tag:
                    move.line_ids._l10n_bg_remove_tax_tag(
                        old_tag, old_tag.l10n_bg_tax_partner_id
                    )
                if track_tag and new_tag and old_tag != new_tag:
                    move.line_ids._l10n_bg_apply_tax_tag(new_tag)
        return res
