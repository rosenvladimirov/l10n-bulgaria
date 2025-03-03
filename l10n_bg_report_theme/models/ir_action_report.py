# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo import models, tools
from odoo.tools.misc import format_date, format_datetime, format_time

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_rendering_context(self, report, docids, data):
        values = super()._get_rendering_context(report, docids, data)
        env = self.env
        _logger.warning(f"REPORT {values}")
        values.update(
            {
                "format_date": lambda date,
                lang_code=False,
                date_format=False: format_date(
                    env, date, lang_code=lang_code, date_format=date_format
                ),
                "format_datetime": lambda dt,
                tz=False,
                dt_format=False,
                lang_code=False: format_datetime(
                    env, dt, tz=tz, dt_format=dt_format, lang_code=lang_code
                ),
                "format_time": lambda time,
                tz=False,
                time_format=False,
                lang_code=False: format_time(
                    env, time, tz=tz, time_format=time_format, lang_code=lang_code
                ),
                "format_amount": lambda amount,
                currency,
                lang_code=False: tools.format_amount(env, amount, currency, lang_code),
                "format_duration": lambda value: tools.format_duration(value),
            }
        )
        # _logger.info(f"REPORT {values}")
        return values
