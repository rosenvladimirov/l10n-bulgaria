# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models


class HrLeaveAllocation(models.Model):
    """Pro-rata annual-leave allocation per BG LC art. 155.

    Adds a helper method that computes the proportional number of leave
    days an employee is entitled to in a calendar year, based on their
    actual months of service that year (hire ↔ termination boundaries).
    """
    _inherit = 'hr.leave.allocation'

    @api.model
    def l10n_bg_compute_pro_rata_days(
        self,
        annual_days,
        period_start,
        period_end,
        active_from=None,
        active_to=None,
    ):
        """Pro-rate annual leave by months of active service.

        Per BG LC art. 155 — annual paid leave is computed proportionally
        when the employee is in service for less than a full calendar year.

        Convention: count whole months only. A month starting on or before
        the 16th counts as a full month; otherwise it is dropped (matches
        common Bulgarian HR practice; customers may override).

        :param annual_days: int|float — base annual days entitlement
            (typically 20 for basic paid leave per LC art. 155 par. 1).
        :param period_start: date — start of the entitlement period
            (typically Jan 1 of the year).
        :param period_end: date — end of the entitlement period
            (typically Dec 31 of the year).
        :param active_from: date|False — when active service begins
            (defaults to period_start if not set).
        :param active_to: date|False — when active service ends
            (defaults to period_end if not set).
        :return: float — pro-rated days, rounded to 1 decimal.
        """
        if active_from is None:
            active_from = period_start
        if active_to is None:
            active_to = period_end

        effective_from = max(active_from, period_start)
        effective_to = min(active_to, period_end)

        if effective_to < effective_from:
            return 0.0

        months = self._l10n_bg_count_pro_rata_months(effective_from, effective_to)
        if months >= 12:
            return float(annual_days)
        return round(annual_days * months / 12.0, 1)

    @staticmethod
    def _l10n_bg_count_pro_rata_months(date_from, date_to):
        """Count whole months between date_from and date_to inclusive.

        Bulgarian-practice convention: a month is counted as whole when
        the employee was in service for at least half the month
        (entered on or before the 16th — or already in service at month
        start; left on or after the 16th — or still in service at
        month end).

        :param date_from: date
        :param date_to: date
        :return: int
        """
        if date_to < date_from:
            return 0
        count = 0
        year_from, month_from = date_from.year, date_from.month
        year_to, month_to = date_to.year, date_to.month
        y, m = year_from, month_from
        while (y, m) <= (year_to, month_to):
            # Month boundaries
            first_of_month = date(y, m, 1)
            if m == 12:
                last_of_month = date(y, 12, 31)
            else:
                last_of_month = date(y, m + 1, 1).replace(day=1) \
                    .toordinal()
                last_of_month = date.fromordinal(last_of_month - 1)
            # Active days within month boundaries
            month_start = max(first_of_month, date_from)
            month_end = min(last_of_month, date_to)
            # Half-month rule: if active for ≥ 16 days OR includes the 1st
            # AND extends past the 15th, count as full month
            active_days = (month_end - month_start).days + 1
            mid_month = date(y, m, 16)
            spans_mid = month_start <= mid_month <= month_end
            if active_days >= 16 or spans_mid:
                count += 1
            # advance
            if m == 12:
                y += 1
                m = 1
            else:
                m += 1
        return count
