#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class L10nBgVatRatioHistory(models.Model):
    _name = "l10n.bg.vat.ratio.history"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Bulgarian VAT Ratio History (Art. 73, Para. 5)"
    _order = "company_id, year desc, month desc"
    _rec_name = "display_name"
    _check_company_auto = True

    year = fields.Integer(
        string="Year",
        required=True,
        default=lambda self: fields.Date.today().year,
        help="Year for which the ratio applies",
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
        help="Leave empty for annual coefficient",
    )
    period_type = fields.Selection(
        [
            ("monthly", "Monthly"),
            ("annual", "Annual"),
        ],
        string="Period Type",
        compute="_compute_period_type",
        store=True,
    )
    date_from = fields.Date(
        string="Valid From",
        required=True,
        compute="_compute_dates",
        store=True,
        readonly=False,
        help="First day of the period",
    )
    date_to = fields.Date(
        string="Valid To",
        required=True,
        compute="_compute_dates",
        store=True,
        readonly=False,
        help="Last day of the period",
    )

    vat_ratio = fields.Float(
        string="VAT Ratio (Art. 73, Para. 2)",
        required=True,
        digits=(5, 2),
        default=0.0,
        help="VAT ratio coefficient according to Art. 73, Para. 2 of VAT Act (in percentage). "
             "Rounded to second decimal place.",
        tracking=True,
    )

    # Numerator (Числител) - Art. 73, Para. 3
    numerator_box_11 = fields.Monetary(
        string="Box 11 - Taxable Supplies",
        currency_field="currency_id",
        default=0.0,
        help="Tax base of taxable supplies (Art. 73, Para. 3, Item 1)",
    )
    numerator_box_13 = fields.Monetary(
        string="Box 13 - Received Payments",
        currency_field="currency_id",
        default=0.0,
        help="Tax base of received payments before taxable event (Art. 73, Para. 3, Item 2)",
    )
    numerator_box_14 = fields.Monetary(
        string="Box 14 - Supplies Outside EU (Art. 69, Para. 2)",
        currency_field="currency_id",
        default=0.0,
        help="Tax base of supplies with place of performance outside Bulgaria, "
             "equated to taxable (Art. 73, Para. 3, Item 3)",
    )
    numerator_box_15 = fields.Monetary(
        string="Box 15 - Payments for Box 14",
        currency_field="currency_id",
        default=0.0,
        help="Payments before supplies from Box 14 (Art. 73, Para. 3, Item 4)",
    )
    numerator_box_16 = fields.Monetary(
        string="Box 16 - Supplies without Tax Credit (Art. 70, Para. 1, Items 3-5)",
        currency_field="currency_id",
        default=0.0,
        help="Tax base of supplies without exercised tax credit right (Art. 73, Para. 3, Item 5)",
    )

    numerator_total = fields.Monetary(
        string="Total Numerator",
        currency_field="currency_id",
        compute="_compute_numerator_denominator",
        store=True,
        help="Total numerator according to Art. 73, Para. 3",
    )

    # Denominator additions (Знаменател - допълнения към числителя) - Art. 73, Para. 4
    denominator_box_17 = fields.Monetary(
        string="Box 17 - Supplies Outside Bulgaria (not Art. 69, Para. 2)",
        currency_field="currency_id",
        default=0.0,
        help="Tax base of supplies outside Bulgaria not equated to taxable (Art. 73, Para. 4, Item 2)",
    )
    denominator_box_18 = fields.Monetary(
        string="Box 18 - Exempt Supplies (excl. Art. 50, Para. 1, Item 2)",
        currency_field="currency_id",
        default=0.0,
        help="Tax base of exempt supplies, excluding financial services (Art. 73, Para. 4, Item 3)",
    )
    denominator_box_19 = fields.Monetary(
        string="Box 19 - Non-Economic Activities",
        currency_field="currency_id",
        default=0.0,
        help="Value of supplies outside economic activity scope (Art. 73, Para. 4, Item 4)",
    )
    denominator_box_42 = fields.Monetary(
        string="Box 42 - Received Subsidies",
        currency_field="currency_id",
        default=0.0,
        help="Amount of received subsidies not included in tax base (Art. 73, Para. 4, Item 6)",
    )

    denominator_total = fields.Monetary(
        string="Total Denominator",
        currency_field="currency_id",
        compute="_compute_numerator_denominator",
        store=True,
        help="Total denominator according to Art. 73, Para. 4",
    )

    # Metadata
    is_manual = fields.Boolean(
        string="Manual Entry",
        default=False,
        help="Check if ratio is entered manually (no data in Odoo)",
        tracking=True,
    )

    is_computed = fields.Boolean(
        string="Computed from VAT Declarations",
        default=False,
        help="Check if ratio was computed automatically from VAT declaration data",
        tracking=True,
    )

    is_provisional = fields.Boolean(
        string="Provisional",
        default=False,
        help="Provisional coefficient for current period, to be adjusted at year end",
        tracking=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        compute="_compute_currency_id",
        store=True,
        precompute=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
        check_company=True,
    )

    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True,
    )

    notes = fields.Text(
        string="Notes",
        help="Additional information about this ratio calculation",
    )

    active = fields.Boolean(
        string="Active",
        default=True,
    )

    _sql_constraints = [
        (
            "unique_year_month_company",
            "UNIQUE(year, month, company_id)",
            "A VAT ratio for this period already exists for this company!",
        ),
        (
            "check_ratio_range",
            "CHECK(vat_ratio >= 0 AND vat_ratio <= 100)",
            "VAT ratio must be between 0 and 100!",
        ),
    ]

    @api.depends("company_id")
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.company_id.currency_id or self.env.ref("base.BGN", raise_if_not_found=False)

    @api.depends("month")
    def _compute_period_type(self):
        for record in self:
            record.period_type = "monthly" if record.month else "annual"

    @api.depends("year", "month")
    def _compute_dates(self):
        for record in self:
            if record.year:
                if record.month:
                    # Monthly period
                    month_int = int(record.month)
                    record.date_from = fields.Date(record.year, month_int, 1)
                    if month_int == 12:
                        record.date_to = fields.Date(record.year, 12, 31)
                    else:
                        next_month = fields.Date(record.year, month_int + 1, 1)
                        record.date_to = next_month - timedelta(days=1)
                else:
                    # Annual period
                    record.date_from = fields.Date(record.year, 1, 1)
                    record.date_to = fields.Date(record.year, 12, 31)

    @api.depends(
        "numerator_box_11",
        "numerator_box_13",
        "numerator_box_14",
        "numerator_box_15",
        "numerator_box_16",
        "denominator_box_17",
        "denominator_box_18",
        "denominator_box_19",
        "denominator_box_42",
    )
    def _compute_numerator_denominator(self):
        for record in self:
            # Calculate numerator (Art. 73, Para. 3)
            record.numerator_total = (
                record.numerator_box_11
                + record.numerator_box_13
                + record.numerator_box_14
                + record.numerator_box_15
                + record.numerator_box_16
            )

            # Calculate denominator (Art. 73, Para. 4)
            record.denominator_total = (
                record.numerator_total
                + record.denominator_box_17
                + record.denominator_box_18
                + record.denominator_box_19
                + record.denominator_box_42
            )

            # Calculate ratio
            if record.denominator_total > 0:
                ratio = (record.numerator_total / record.denominator_total) * 100
                # Round to second decimal place (up)
                record.vat_ratio = self._round_vat_ratio(ratio)
            else:
                record.vat_ratio = 0.0

    @api.depends("year", "month", "vat_ratio", "company_id", "period_type")
    def _compute_display_name(self):
        for record in self:
            company_name = record.company_id.name if record.company_id else ""
            if record.month:
                month_name = dict(self._fields["month"].selection)[record.month]
                record.display_name = f"[{company_name}] {month_name} {record.year} - {record.vat_ratio:.2f}%"
            else:
                record.display_name = f"[{company_name}] {record.year} (Annual) - {record.vat_ratio:.2f}%"

    @staticmethod
    def _round_vat_ratio(ratio):
        """
        Round VAT ratio to second decimal place according to Bulgarian tax rules.
        Rules: {0.120…1, 0.122, 0.123, 0.124, 0.125} = 0.13
               {0.126, 0.127, 0.128, 0.129} = 0.13
        Essentially rounds up at 0.005
        """
        import math
        return math.ceil(ratio * 100) / 100

    @api.constrains("numerator_total", "denominator_total", "vat_ratio", "is_manual")
    def _check_ratio_calculation(self):
        for record in self:
            if not record.is_manual and record.denominator_total > 0:
                computed_ratio = (record.numerator_total / record.denominator_total) * 100
                computed_ratio_rounded = self._round_vat_ratio(computed_ratio)
                if abs(computed_ratio_rounded - record.vat_ratio) > 0.01:
                    raise ValidationError(
                        _(
                            "The VAT ratio (%.2f%%) does not match the calculated ratio (%.2f%%)."
                        )
                        % (record.vat_ratio, computed_ratio_rounded)
                    )

    @api.onchange(
        "numerator_box_11",
        "numerator_box_13",
        "numerator_box_14",
        "numerator_box_15",
        "numerator_box_16",
        "denominator_box_17",
        "denominator_box_18",
        "denominator_box_19",
        "denominator_box_42",
    )
    def _onchange_boxes(self):
        """Recalculate when boxes change."""
        if not self.is_manual:
            self.is_computed = True
            self.is_manual = False

    @api.model
    def get_ratio_for_period(self, year, month=None, company=None):
        """Get the VAT ratio for a specific period and company."""
        if not company:
            company = self.env.company

        self = self.with_company(company)

        domain = [
            ("year", "=", year),
            ("company_id", "=", company.id),
            ("active", "=", True),
        ]

        if month:
            domain.append(("month", "=", str(month)))
        else:
            domain.append(("month", "=", False))

        ratio = self.search(domain, limit=1)
        return ratio.vat_ratio if ratio else 0.0

    @api.model
    def compute_ratio_from_vat_declarations(self, year, month=None, company=None):
        """
        Compute VAT ratio from VAT declaration data (boxes 11, 13, 14, 15, 16, 17, 18, 19, 42).
        According to Art. 73 of the Bulgarian VAT Act.
        Uses account.bg.vat.calc.declar model for data consistency.

        If no data exists for the period, returns the last known coefficient.
        """
        if not company:
            company = self.env.company

        self = self.with_company(company)

        if month:
            date_from = fields.Date(year, month, 1)
            if month == 12:
                date_to = fields.Date(year, 12, 31)
            else:
                next_month = fields.Date(year, month + 1, 1)
                date_to = next_month - timedelta(days=1)
            tax_period = f"{year}{str(month).zfill(2)}"
        else:
            # Annual calculation
            date_from = fields.Date(year, 1, 1)
            date_to = fields.Date(year, 12, 31)
            tax_period = None

        # Use the predefined _table_query from account.bg.vat.calc.declar
        calc_declar_query = self.env['account.bg.vat.calc.declar']._table_query

        if tax_period:
            # Monthly calculation
            query = f"""
                SELECT
                    company_id,
                    COALESCE(SUM(account_tag_11), 0.0) AS box_11,
                    COALESCE(SUM(account_tag_13), 0.0) AS box_13,
                    COALESCE(SUM(account_tag_14), 0.0) AS box_14,
                    COALESCE(SUM(account_tag_15), 0.0) AS box_15,
                    COALESCE(SUM(account_tag_16), 0.0) AS box_16,
                    COALESCE(SUM(account_tag_17), 0.0) AS box_17,
                    COALESCE(SUM(account_tag_18), 0.0) AS box_18,
                    COALESCE(SUM(account_tag_19), 0.0) AS box_19,
                    COALESCE(SUM(account_tag_42), 0.0) AS box_42
                FROM ({calc_declar_query}) AS vat_calc
                WHERE
                    company_id = %s
                    AND info_tag_3 = %s
                GROUP BY company_id
            """
            params = (company.id, tax_period)
        else:
            # Annual calculation - sum all months
            query = f"""
                SELECT
                    company_id,
                    COALESCE(SUM(account_tag_11), 0.0) AS box_11,
                    COALESCE(SUM(account_tag_13), 0.0) AS box_13,
                    COALESCE(SUM(account_tag_14), 0.0) AS box_14,
                    COALESCE(SUM(account_tag_15), 0.0) AS box_15,
                    COALESCE(SUM(account_tag_16), 0.0) AS box_16,
                    COALESCE(SUM(account_tag_17), 0.0) AS box_17,
                    COALESCE(SUM(account_tag_18), 0.0) AS box_18,
                    COALESCE(SUM(account_tag_19), 0.0) AS box_19,
                    COALESCE(SUM(account_tag_42), 0.0) AS box_42
                FROM ({calc_declar_query}) AS vat_calc
                WHERE
                    company_id = %s
                    AND info_tag_3 LIKE %s
                GROUP BY company_id
            """
            params = (company.id, f"{year}%")

        self.env.cr.execute(query, params)
        result = self.env.cr.dictfetchone()

        # Initialize boxes
        boxes = {
            "11": 0.0,
            "13": 0.0,
            "14": 0.0,
            "15": 0.0,
            "16": 0.0,
            "17": 0.0,
            "18": 0.0,
            "19": 0.0,
            "42": 0.0,
        }

        # Check if we have data
        has_data = False
        if result:
            for key in boxes.keys():
                box_value = result.get(f"box_{key}", 0.0) or 0.0
                boxes[key] = box_value
                if abs(box_value) > 0.01:  # Consider values > 0.01 as data
                    has_data = True

        # If no data found, try to get last known coefficient
        if not has_data:
            _logger.info(
                f"No VAT declaration data found for period {tax_period or year}. "
                f"Searching for last known coefficient."
            )

            domain = [
                ("company_id", "=", company.id),
                ("active", "=", True),
            ]

            if month:
                # For monthly calculation, look for previous months or years
                domain.extend([
                    "|",
                    ("year", "<", year),
                    "&",
                    ("year", "=", year),
                    ("month", "<", str(month)),
                ])
            else:
                # For annual calculation, look for previous years
                domain.append(("year", "<", year))

            last_ratio = self.search(domain, order="year desc, month desc", limit=1)

            if last_ratio:
                _logger.info(
                    f"Found last known coefficient: {last_ratio.display_name} = {last_ratio.vat_ratio}%"
                )
                return {
                    "vat_ratio": last_ratio.vat_ratio,
                    "numerator_box_11": last_ratio.numerator_box_11,
                    "numerator_box_13": last_ratio.numerator_box_13,
                    "numerator_box_14": last_ratio.numerator_box_14,
                    "numerator_box_15": last_ratio.numerator_box_15,
                    "numerator_box_16": last_ratio.numerator_box_16,
                    "denominator_box_17": last_ratio.denominator_box_17,
                    "denominator_box_18": last_ratio.denominator_box_18,
                    "denominator_box_19": last_ratio.denominator_box_19,
                    "denominator_box_42": last_ratio.denominator_box_42,
                    "numerator_total": last_ratio.numerator_total,
                    "denominator_total": last_ratio.denominator_total,
                    "is_manual": True,
                    "is_computed": False,
                    "is_provisional": bool(month),  # Monthly is provisional
                    "notes": _("No VAT declaration data found for period %s. "
                               "Values copied from last known coefficient: %s (%.2f%%)")
                             % (tax_period or year, last_ratio.display_name, last_ratio.vat_ratio),
                }
            else:
                _logger.warning(
                    f"No previous coefficient found for company {company.name}. "
                    f"Manual entry required."
                )

        # Calculate numerator (Art. 73, Para. 3)
        numerator_total = (
            boxes["11"]  # Taxable supplies
            + boxes["13"]  # Received payments before taxable event
            + boxes["14"]  # Supplies outside Bulgaria (Art. 69, Para. 2)
            + boxes["15"]  # Payments for Box 14
            + boxes["16"]  # Supplies without tax credit (Art. 70, Para. 1, Items 3-5)
        )

        # Calculate denominator (Art. 73, Para. 4)
        denominator_total = (
            numerator_total
            + boxes["17"]  # Supplies outside Bulgaria (not Art. 69, Para. 2)
            + boxes["18"]  # Exempt supplies (excluding Art. 50, Para. 1, Item 2)
            + boxes["19"]  # Non-economic activities
            + boxes["42"]  # Received subsidies (note: box_42 is actually from purchases, might need adjustment)
        )

        # Calculate ratio
        vat_ratio = 0.0
        if denominator_total > 0:
            ratio = (numerator_total / denominator_total) * 100
            vat_ratio = self._round_vat_ratio(ratio)
            _logger.info(
                f"VAT ratio calculated for period {tax_period or year}: "
                f"{numerator_total:.2f} / {denominator_total:.2f} = {vat_ratio:.2f}%"
            )
        else:
            _logger.warning(
                f"Denominator is zero for period {tax_period or year}. "
                f"Cannot calculate ratio."
            )

        return {
            "vat_ratio": vat_ratio,
            "numerator_box_11": boxes["11"],
            "numerator_box_13": boxes["13"],
            "numerator_box_14": boxes["14"],
            "numerator_box_15": boxes["15"],
            "numerator_box_16": boxes["16"],
            "denominator_box_17": boxes["17"],
            "denominator_box_18": boxes["18"],
            "denominator_box_19": boxes["19"],
            "denominator_box_42": boxes["42"],
            "numerator_total": numerator_total,
            "denominator_total": denominator_total,
            "is_manual": not has_data,
            "is_computed": has_data,
            "is_provisional": bool(month) and has_data,  # Monthly computed is provisional
            "notes": "" if has_data else _("No VAT declaration data found for period %s. Manual entry required.") % (
                    tax_period or year),
        }

    def action_compute_from_declarations(self):
        """Action to compute ratio from VAT declarations."""
        self.ensure_one()
        month = int(self.month) if self.month else None

        try:
            result = self.compute_ratio_from_vat_declarations(
                self.year,
                month,
                self.company_id
            )

            self.write({
                "vat_ratio": result["vat_ratio"],
                "numerator_box_11": result["numerator_box_11"],
                "numerator_box_13": result["numerator_box_13"],
                "numerator_box_14": result["numerator_box_14"],
                "numerator_box_15": result["numerator_box_15"],
                "numerator_box_16": result["numerator_box_16"],
                "denominator_box_17": result["denominator_box_17"],
                "denominator_box_18": result["denominator_box_18"],
                "denominator_box_19": result["denominator_box_19"],
                "denominator_box_42": result["denominator_box_42"],
                "is_computed": result["is_computed"],
                "is_manual": result["is_manual"],
                "is_provisional": result["is_provisional"],
                "notes": result.get("notes", self.notes or ""),
            })

            # Prepare notification message
            if result["is_computed"]:
                message = _(
                    "VAT ratio computed from declarations: %.2f%%\n"
                    "Numerator: %.2f %s\n"
                    "Denominator: %.2f %s\n"
                    "%s"
                ) % (
                              result["vat_ratio"],
                              result["numerator_total"],
                              self.currency_id.symbol,
                              result["denominator_total"],
                              self.currency_id.symbol,
                              _("(Provisional - will be adjusted at year end)") if result["is_provisional"] else "",
                          )
                notification_type = "success"
                sticky = False
            else:
                if "copied from last known coefficient" in result.get("notes", ""):
                    message = result["notes"]
                    notification_type = "warning"
                    sticky = True
                else:
                    message = _(
                        "No VAT declaration data found for this period.\n"
                        "No previous coefficient found either.\n"
                        "Please enter values manually."
                    )
                    notification_type = "warning"
                    sticky = True

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("VAT Ratio Calculation (Art. 73)"),
                    "message": message,
                    "type": notification_type,
                    "sticky": sticky,
                },
            }
        except Exception as e:
            _logger.error(f"Error computing VAT ratio: {str(e)}", exc_info=True)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _("Error computing VAT ratio: %s") % str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def action_compute_from_declarations(self):
        """Action to compute ratio from VAT declarations."""
        self.ensure_one()
        month = int(self.month) if self.month else None
        result = self.compute_ratio_from_vat_declarations(
            self.year,
            month,
            self.company_id
        )
        self.write({
            **result,
            "is_computed": True,
            "is_manual": False,
        })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _(
                    "VAT ratio computed from declarations: %.2f%%\n"
                    "Numerator: %.2f BGN\n"
                    "Denominator: %.2f BGN"
                ) % (result["vat_ratio"], result["numerator_total"], result["denominator_total"]),
                "type": "success",
                "sticky": False,
            },
        }

    def action_calculate_annual_adjustment(self):
        """
        Calculate annual adjustment according to Art. 73, Para. 8.
        Formula: ГК = ДПЧДК x КТГ - ПЧДКТГ
        """
        self.ensure_one()

        if self.month:
            raise ValidationError(
                _("Annual adjustment can only be calculated for annual coefficients (without month).")
            )

        # Get all monthly ratios for the year
        monthly_ratios = self.search([
            ("year", "=", self.year),
            ("month", "!=", False),
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
        ])

        if not monthly_ratios:
            raise ValidationError(
                _("No monthly ratios found for year %s. Cannot calculate adjustment.") % self.year
            )

        # This is a placeholder - actual implementation depends on your partial VAT credit tracking
        # You need to track:
        # - ДПЧДК (Tax with right to partial VAT credit for current year)
        # - ПЧДКТГ (Total partial VAT credit used during current year)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Information"),
                "message": _(
                    "Annual adjustment calculation requires tracking of partial VAT credits. "
                    "This should be implemented in the VAT return module."
                ),
                "type": "info",
                "sticky": True,
            },
        }

    def name_get(self):
        """Custom name_get to show company in the name."""
        result = []
        for record in self:
            name = record.display_name
            result.append((record.id, name))
        return result
