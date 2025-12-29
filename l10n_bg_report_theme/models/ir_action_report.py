#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging

from odoo import models, tools, fields
from odoo.tools.misc import format_date, format_datetime, format_time

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_rendering_context(self, report, docids, data):
        values = super()._get_rendering_context(report, docids, data)
        env = self.env

        def safe_format_date(date, lang_code=False, date_format=False, widget=False):
            """Safe wrapper that formats date WITH time if it's a datetime object"""
            if not date:
                return ''

            # Ако е datetime.datetime, използваме format_datetime
            if isinstance(date, datetime.datetime):
                try:
                    # Използваме format_datetime БЕЗ dt_format параметъра
                    # Нека Odoo избере подходящия формат
                    if widget == 'date':
                        return format_date(env, date, lang_code=lang_code)
                    return format_datetime(env, date, tz=False, dt_format=date_format, lang_code=lang_code)
                except Exception as e:
                    _logger.error(f"Error in format_datetime: {e}")
                    # Fallback към strftime с дата и час
                    if widget == 'date':
                        return date.strftime('%d.%m.%Y')
                    return date.strftime('%d.%m.%Y %H:%M')

            # Ако е само date, използваме format_date
            else:
                try:
                    return format_date(env, date, lang_code=lang_code, date_format=date_format)
                except Exception as e:
                    _logger.error(f"Error in format_date: {e}")
                    # Fallback към strftime само с дата
                    return date.strftime('%d.%m.%Y')

        values.update(
            {
                "format_date": safe_format_date,
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
        return values
