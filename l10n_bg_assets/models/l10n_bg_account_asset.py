# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.tools import float_compare
from odoo.tools.date_utils import add

_logger = logging.getLogger(__name__)


def date_range(start_date, end_date):
    """
    Generate dates from start_date to end_date (inclusive).

    This is a replacement for odoo.tools.date_range which was removed in Odoo 19.

    Args:
        start_date (date): Start date
        end_date (date): End date

    Yields:
        date: Each date from start_date to end_date

    Example:
        >>> from datetime import date
        >>> list(date_range(date(2024, 1, 1), date(2024, 1, 3)))
        [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    """
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


class AccountAsset(models.Model):
    _inherit = "account.asset"

    name = fields.Char(translate=True)
    l10n_bg_depreciation_ids = fields.One2many(
        "bg.account.asset.depreciation.board",
        inverse_name="asset_id",
        string="BG law Depreciation",
    )
    l10n_bg_freeze_period_ids = fields.One2many(
        "bg.account.asset.freeze.periods",
        inverse_name="asset_id",
        string="Freeze periods",
    )
    l10n_bg_method_percentage = fields.Float(string="Percentage Depreciation")
    l10n_bg_tax_model_id = fields.Many2one(
        "account.asset",
        string="Tax Model",
        change_default=True,
        domain="[('company_id', '=', company_id)]",
    )
    l10n_bg_tax_model = fields.Boolean(string="Is Tax Model")
    l10n_bg_disposal_date = fields.Date(string="BG Tax Disposal Date")
    l10n_bg_depreciation_tax_count = fields.Integer(
        "Tax depreciation line count",
        compute="_compute_l10n_bg_depreciation_tax_count"
    )
    paused_prorata_date = fields.Date(string="Paused Prorata Date")

    @api.depends("l10n_bg_depreciation_ids")
    def _compute_l10n_bg_depreciation_tax_count(self):
        for record in self:
            record.l10n_bg_depreciation_tax_count = len(record.l10n_bg_depreciation_ids.filtered(lambda x: x.method_percentage != 0.0))

    @api.onchange("l10n_bg_tax_model_id")
    def _onchange_l10n_bg_tax_model_id(self):
        model = self.l10n_bg_tax_model_id
        if model:
            self.l10n_bg_method_percentage = model.l10n_bg_method_percentage

    def _get_freeze_periods(self, bg_period_end_date):
        paused_prorata_date = datetime.combine(
            self.paused_prorata_date, datetime.min.time()
        )
        end_paused_prorata_date = datetime.combine(
            self.company_id.compute_fiscalyear_dates(paused_prorata_date).get("date_to"),
            datetime.min.time()
        )
        paused_prorata_dates = date_range(paused_prorata_date, end_paused_prorata_date)
        paused_mounts = relativedelta(
            end_paused_prorata_date, paused_prorata_date
        ).months
        add_year = paused_mounts // 12
        if paused_mounts // 12 >= 1:
            bg_period_end_date = add(bg_period_end_date, year=add_year)
        return paused_prorata_dates, paused_mounts, add_year, bg_period_end_date

    def _recompute_board(self, start_depreciation_date=False):
        self.ensure_one()
        depreciation_move_values = super()._recompute_board(
            start_depreciation_date=start_depreciation_date
        )
        self.l10n_bg_depreciation_ids = [Command.clear()]

        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
            lambda mv: mv.state == "posted" and not mv.asset_value_change
        ).sorted(key=lambda mv: (mv.date, mv.id))

        imported_amount = self.already_depreciated_amount_import
        residual_amount = self.value_residual
        if not posted_depreciation_move_ids:
            residual_amount += imported_amount

        sequence = 0
        l10n_bg_method_percentage = self.l10n_bg_method_percentage / 100 if self.l10n_bg_method_percentage != 0.0 else 0.0
        if l10n_bg_method_percentage == 0.0:
            standard_depreciation_value = 0.0
            months = 0
            years = 0
        else:
            standard_depreciation_value = residual_amount * l10n_bg_method_percentage / 12
            months = int(1 / l10n_bg_method_percentage * 12)
            years = months // 12
            months = int((months / 12 - months // 12) * 12)
        bg_period_start_date = (
            self.prorata_date == self.prorata_date.replace(day=1)
            and self.prorata_date
            or self.prorata_date + relativedelta(months=1)
        )
        bg_period_start_date = bg_period_start_date.replace(day=1)
        bg_period_start_date = datetime.combine(
            bg_period_start_date, datetime.min.time()
        )

        bg_period_end_date = (
            (bg_period_start_date + relativedelta(months=1))
            + relativedelta(days=-1)
            + relativedelta(months=months, years=years)
            + relativedelta(months=-1)
        )
        bg_period_end_date = datetime.combine(bg_period_end_date, datetime.min.time())

        # _logger.info(f"Months: {months} Years: {years} Start: {bg_period_start_date} End: {bg_period_end_date}")

        fiscal_period_total_depreciation_value = total_depreciation_value = 0.0
        (
            paused_prorata_dates,
            paused_mounts,
            add_year,
            bg_period_end_date,
        ) = self._get_freeze_periods(bg_period_end_date)

        l10n_bg_depreciation_ids = [
            Command.create(
                {
                    "sequence": sequence,
                    "init_entry": True,
                    "value_residual": residual_amount,
                    "original_value": self.original_value,
                    "salvage_value": self.salvage_value,
                    "prorata_date": self.prorata_date,
                    "line_date": bg_period_start_date,
                    "method_percentage": self.l10n_bg_method_percentage,
                }
            )
        ]

        if self.l10n_bg_method_percentage == 0.0:
            return depreciation_move_values

        # _logger.info(f"{paused_prorata_dates} {paused_mounts} {add_year} {bg_period_start_date} {bg_period_end_date}")

        for period in date_range(bg_period_start_date, bg_period_end_date):
            sequence += 1
            fiscalyear_dates = self.company_id.compute_fiscalyear_dates(period)
            depreciation_value = standard_depreciation_value
            # days_in_fiscalyear = self._get_delta_days(fiscalyear_dates['date_from'], fiscalyear_dates['date_to'])
            if fiscalyear_dates and fiscalyear_dates["date_from"] == period:
                if paused_mounts >= 12:
                    depreciation_value = -fiscal_period_total_depreciation_value
                fiscal_period_total_depreciation_value = 0.0
            total_depreciation_value += depreciation_value
            fiscal_period_total_depreciation_value += depreciation_value
            if not float_compare(residual_amount, depreciation_value, 2) > 0:
                depreciation_value = residual_amount
            residual_amount -= depreciation_value
            period = (period.replace(day=1) + relativedelta(months=1)) + relativedelta(
                days=-1
            )
            l10n_bg_depreciation_ids.append(
                Command.create(
                    {
                        "sequence": sequence,
                        "line_date": period,
                        "value_residual": residual_amount,
                        "value": depreciation_value,
                        "ref": f"{self.display_name}: {l10n_bg_method_percentage*100:.2f}%",
                    }
                )
            )
        self.update(
            {
                "l10n_bg_depreciation_ids": l10n_bg_depreciation_ids,
                "l10n_bg_disposal_date": bg_period_start_date,
            }
        )
        return depreciation_move_values

    def set_to_cancelled(self):
        for asset in self:
            asset.l10n_bg_depreciation_ids = [Command.clear()]
        return super().set_to_cancelled()
