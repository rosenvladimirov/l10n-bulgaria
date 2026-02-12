#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json

from odoo import Command, _, api, fields, models

L10N_BG_INTRASTAT = [
    ("standard", "Standard base on levelling up"),
    ("statistical", "Statistical base on levelling up"),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_bg_audit_use_tax = fields.Boolean(
        string="Use Forced Customs Tax",
        help="Enable audit tax handling force customs type calculation reports.",
    )

    l10n_bg_odoo_compatible = fields.Boolean("Odoo compatible")
    l10n_bg_tax_contact_id = fields.Many2one(
        "res.partner",
        string="TAX Report creator",
        compute="_compute_l10n_bg_tax_contact_id",
        inverse="_inverse_l10n_bg_tax_contact_id",
        store=True,
    )

    l10n_bg_intra_stat_type = fields.Selection(
        L10N_BG_INTRASTAT, string="Level of registration",
        compute="_compute_l10n_bg_intrastat_fields",
        inverse="_inverse_l10n_bg_intrastat_fields",
        store=True,
    )
    l10n_bg_intra_stat_incomes = fields.Boolean(
        "An obligation to submit intra-Community supplies",
        compute="_compute_l10n_bg_intrastat_fields",
        inverse="_inverse_l10n_bg_intrastat_fields",
        store=True,
    )
    l10n_bg_intra_stat_outcomes = fields.Boolean(
        "An obligation to submit intra-Community incomes",
        compute="_compute_l10n_bg_intrastat_fields",
        inverse="_inverse_l10n_bg_intrastat_fields",
        store=True,
    )

    # VAT Ratio fields
    l10n_bg_vat_ratio = fields.Float(
        string="VAT Ratio (Art. 73)",
        default=0.0,
        help="Annual VAT ratio coefficient according to Art. 73, Para. 2 of VAT Act. "
             "This is automatically updated from the current fiscal year's annual VAT ratio history.",
    )

    l10n_bg_vat_ratio_history_id = fields.Many2one(
        "l10n.bg.vat.ratio.history",
        string="Current VAT Ratio History",
        compute="_compute_l10n_bg_vat_ratio_history_id",
        inverse="_inverse_l10n_bg_vat_ratio_history_id",
        store=True,
        help="Link to the current fiscal year's annual VAT ratio history record",
    )

    l10n_bg_intrastat_threshold_id = fields.Many2one(
        "l10n.bg.intrastat.threshold",
        string="Current Intrastat Threshold",
        compute="_compute_l10n_bg_intrastat_threshold_id",
        inverse="_inverse_l10n_bg_intrastat_threshold_id",
        store=True,
        help="Link to the most recent month's Intrastat threshold record",
    )

    @api.depends("partner_id")
    def _compute_l10n_bg_tax_contact_id(self):
        for record in self:
            l10n_bg_tax_contact_id = record.partner_id.child_ids.filtered(
                lambda r: r.type == "represent"
            )
            if len(l10n_bg_tax_contact_id) > 1:
                l10n_bg_tax_contact_id = l10n_bg_tax_contact_id[0]
            record.l10n_bg_tax_contact_id = l10n_bg_tax_contact_id

    @api.depends("partner_id")
    def _inverse_l10n_bg_tax_contact_id(self):
        for record in self:
            if record.l10n_bg_tax_contact_id:
                if record.l10n_bg_tax_contact_id.type not in ["represent", "agent", "tax"]:
                    record.l10n_bg_tax_contact_id.type = "represent"
                record.partner_id.child_ids = [
                    Command.link(record.l10n_bg_tax_contact_id.id)
                ]
            else:
                record.l10n_bg_tax_contact_id = False
                record.partner_id.child_ids.filtered(lambda r: r.id == record.id).type = "contact"

    def _compute_l10n_bg_vat_ratio_history_id(self):
        """Find the annual VAT ratio for the current year."""
        for record in self:
            # Get current year
            current_year = fields.Date.context_today(record).year

            # Find annual VAT ratio history for the current year
            ratio_history = record.env['l10n.bg.vat.ratio.history'].search([
                ('company_id', '=', record.id),
                ('year', '=', current_year),
                ('month', '=', False),  # Annual only
                ('active', '=', True),
            ], limit=1)

            record.l10n_bg_vat_ratio_history_id = ratio_history

            # Update vat_ratio from history if exists
            if ratio_history:
                record.l10n_bg_vat_ratio = ratio_history.vat_ratio
            else:
                record.l10n_bg_vat_ratio = 0.0

    def _inverse_l10n_bg_vat_ratio_history_id(self):
        """Sync VAT ratio when the history record is manually changed."""
        for record in self:
            if record.l10n_bg_vat_ratio_history_id:
                record.l10n_bg_vat_ratio = record.l10n_bg_vat_ratio_history_id.vat_ratio
            else:
                record.l10n_bg_vat_ratio = 0.0

    def _compute_l10n_bg_intrastat_threshold_id(self):
        """Find the Intrastat threshold for the most recent month."""
        for record in self:
            # Get the current date
            today = fields.Date.context_today(record)

            # Find the most recent monthly threshold
            threshold = record.env['l10n.bg.intrastat.threshold'].search([
                ('company_id', '=', record.id),
                ('month', '!=', False),  # Only monthly records
                ('active', '=', True),
                ('date_from', '<=', today),
                '|',
                ('date_to', '=', False),
                ('date_to', '>=', today),
            ], order='year desc, month desc', limit=1)

            record.l10n_bg_intrastat_threshold_id = threshold

    def _inverse_l10n_bg_intrastat_threshold_id(self):
        """Handle manual changes to the threshold record."""
        for record in self:
            # This allows manual linking if needed
            # You can add additional logic here if necessary
            pass

    @api.depends("l10n_bg_intrastat_threshold_id")
    def _compute_l10n_bg_intrastat_fields(self):
        """Compute Intrastat fields based on the current threshold."""
        for record in self:
            threshold = record.l10n_bg_intrastat_threshold_id

            if threshold:
                # Determine a registration type based on thresholds
                has_extended = (
                    threshold.threshold_arrivals_extended > 0 or
                    threshold.threshold_dispatches_extended > 0
                )
                has_standard = (
                    threshold.threshold_arrivals_standard > 0 or
                    threshold.threshold_dispatches_standard > 0
                )

                if has_extended:
                    record.l10n_bg_intra_stat_type = "statistical"
                elif has_standard:
                    record.l10n_bg_intra_stat_type = "standard"
                else:
                    record.l10n_bg_intra_stat_type = False

                # Set obligations based on threshold values
                record.l10n_bg_intra_stat_incomes = (
                    threshold.threshold_dispatches_standard > 0 or
                    threshold.threshold_dispatches_extended > 0
                )
                record.l10n_bg_intra_stat_outcomes = (
                    threshold.threshold_arrivals_standard > 0 or
                    threshold.threshold_arrivals_extended > 0
                )
            else:
                record.l10n_bg_intra_stat_type = False
                record.l10n_bg_intra_stat_incomes = False
                record.l10n_bg_intra_stat_outcomes = False

    def _inverse_l10n_bg_intrastat_fields(self):
        """Allow manual override of Intrastat fields."""
        # This allows manual changes if needed
        # The fields will be recomputed when threshold changes
        pass

    def _process_l10n_bg_report_audit_config_file(self):
        file_content_json = self.l10n_bg_config_template and json.loads(self.l10n_bg_config_template) or {}
        for key, value in file_content_json.get('account.account.tag', {}).items():
            for tag_key, tags in value.items():
                tag_id = self.env['account.account.tag'].search([('name', 'in', list(map(str, tags)))])
                if tag_id:
                    tag_id.write({
                        key: tag_key
                    })
