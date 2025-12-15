#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class L10nBgIntrastatThreshold(models.Model):
    _name = "l10n.bg.intrastat.threshold"
    _description = "Bulgarian Intrastat Threshold History"
    _order = "company_id, year desc, month desc"
    _rec_name = "display_name"
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )

    year = fields.Integer(
        string="Year",
        required=True,
        default=lambda self: fields.Date.today().year,
        help="Year for which the threshold applies",
        tracking=True,
    )
    month = fields.Selection(
        [
            ("1", "January"),
            ("2", "February"),
            ("3", "March"),
            ("4", "April"),
            ("5", "May"),
            ("6", "June"),
            ("7", "July"),
            ("8", "August"),
            ("9", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        string="Month",
        help="Month from which the threshold applies (leave empty for annual threshold)",
        tracking=True,
    )
    date_from = fields.Date(
        string="Valid From",
        required=True,
        default=fields.Date.today,
        help="Date from which this threshold is valid",
        tracking=True,
    )
    date_to = fields.Date(
        string="Valid To",
        help="Date until which this threshold is valid (leave empty for current threshold)",
        tracking=True,
    )

    # Thresholds for arrivals (intra-Community acquisitions)
    threshold_arrivals_extended = fields.Monetary(
        string="Arrivals Threshold - Extended",
        currency_field="currency_id",
        default=0.0,
        help="Extended threshold for intra-Community acquisitions (in BGN)",
        tracking=True,
    )
    threshold_arrivals_standard = fields.Monetary(
        string="Arrivals Threshold - Standard",
        currency_field="currency_id",
        default=0.0,
        help="Standard threshold for intra-Community acquisitions (in BGN)",
        tracking=True,
    )

    # Thresholds for dispatches (intra-Community supplies)
    threshold_dispatches_extended = fields.Monetary(
        string="Dispatches Threshold - Extended",
        currency_field="currency_id",
        default=0.0,
        help="Extended threshold for intra-Community supplies (in BGN)",
        tracking=True,
    )
    threshold_dispatches_standard = fields.Monetary(
        string="Dispatches Threshold - Standard",
        currency_field="currency_id",
        default=0.0,
        help="Standard threshold for intra-Community supplies (in BGN)",
        tracking=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        compute="_compute_currency_id",
        store=True,
        precompute=True,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
        help="Set to false to archive the threshold",
        tracking=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
        check_company=True,
        tracking=True,
    )

    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True,
    )

    notes = fields.Text(
        string="Notes",
        help="Additional information about this threshold change",
        tracking=True,
    )

    _sql_constraints = [
        (
            "unique_year_month_company",
            "UNIQUE(year, month, company_id, date_from)",
            "A threshold for this period already exists for this company!",
        ),
    ]

    @api.depends("company_id")
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.company_id.currency_id or self.env.ref("base.BGN", raise_if_not_found=False)

    @api.depends("year", "month", "company_id")
    def _compute_display_name(self):
        for record in self:
            company_name = record.company_id.name if record.company_id else ""
            if record.month:
                month_name = dict(self._fields["month"].selection)[record.month]
                record.display_name = f"[{company_name}] {month_name} {record.year}"
            else:
                record.display_name = f"[{company_name}] {record.year}"

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError(
                    _("The 'Valid To' date must be after the 'Valid From' date.")
                )

    @api.constrains("year", "month", "date_from")
    def _check_date_consistency(self):
        for record in self:
            if record.month:
                expected_month = int(record.month)
                if record.date_from.month != expected_month:
                    raise ValidationError(
                        _(
                            "The 'Valid From' date must be in the same month as the selected month."
                        )
                    )
            if record.date_from.year != record.year:
                raise ValidationError(
                    _("The 'Valid From' date must be in the same year as the selected year.")
                )

    @api.constrains("company_id", "date_from", "date_to", "year", "month")
    def _check_overlapping_periods(self):
        """Check for overlapping periods within the same company."""
        for record in self:
            domain = [
                ("id", "!=", record.id),
                ("company_id", "=", record.company_id.id),
                ("active", "=", True),
                ("year", "=", record.year),
            ]

            # Add month condition if month is specified
            if record.month:
                domain.append(("month", "=", record.month))

            overlapping = self.search(domain, limit=1)
            if overlapping:
                raise ValidationError(
                    _("Period overlaps with existing threshold: %s") % overlapping.display_name
                )

    @api.model
    def get_threshold_for_date(self, date, company=None):
        """Get the applicable threshold for a specific date and company."""
        if not company:
            company = self.env.company

        domain = [
            ("date_from", "<=", date),
            ("company_id", "=", company.id),
            ("active", "=", True),
            "|",
            ("date_to", "=", False),
            ("date_to", ">=", date),
        ]

        threshold = self.search(domain, order="date_from desc", limit=1)

        if threshold:
            _logger.debug(
                f"Found Intrastat threshold for date {date} and company {company.name}: {threshold.display_name}"
            )
        else:
            _logger.warning(
                f"No Intrastat threshold found for date {date} and company {company.name}"
            )

        return threshold

    @api.model
    def get_current_threshold(self, company=None):
        """Get the current applicable threshold for a company."""
        return self.get_threshold_for_date(fields.Date.today(), company)

    @api.model
    def get_threshold_for_period(self, year, month=None, company=None):
        """Get the threshold for a specific period (year/month) and company."""
        if not company:
            company = self.env.company

        domain = [
            ("year", "=", year),
            ("company_id", "=", company.id),
            ("active", "=", True),
        ]

        if month:
            domain.append(("month", "=", str(month)))
        else:
            domain.append(("month", "=", False))

        threshold = self.search(domain, limit=1)

        if threshold:
            _logger.debug(
                f"Found Intrastat threshold for period {year}/{month or 'Annual'} "
                f"and company {company.name}: {threshold.display_name}"
            )

        return threshold

    def name_get(self):
        """Custom name_get to show the company in the name."""
        result = []
        for record in self:
            name = record.display_name
            result.append((record.id, name))
        return result
