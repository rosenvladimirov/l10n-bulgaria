# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_by_email_get_base_mail_values(self, message, recipients_data, additional_values=None):
        """
        Override за да конвертираме dict names в strings ПРЕДИ да стигнат до formataddr.
        """

        # Почистваме recipients_data от dict names
        for r in recipients_data:
            if isinstance(r.get('name'), dict):
                try:
                    lang = self.env.context.get('lang') or self.env.user.lang or 'en_US'
                    name_value = r['name'].get(lang) or \
                                 r['name'].get('en_US') or \
                                 next(iter(r['name'].values()), '')
                    r['name'] = name_value
                except Exception as e:
                    _logger.warning(f"Error converting dict name: {e}")
                    r['name'] = ''

            # Гарантираме че name е string
            if r.get('name') and not isinstance(r['name'], str):
                try:
                    r['name'] = str(r['name'])
                except Exception:
                    r['name'] = ''

        # Извикваме super() с почистените данни И всички параметри
        return super()._notify_by_email_get_base_mail_values(
            message, recipients_data, additional_values=additional_values
        )
