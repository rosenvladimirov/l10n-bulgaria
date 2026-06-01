# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Закача регистрационния push към EE/publisher „нотифи" cron (тихо).

Стандартният Odoo publisher_warranty cron
(``mail.ir_cron_module_update_notification``, седмичен) вика
``update_notification``. Разширяваме го, за да излъчим и регистрацията
на bus канал ``l10n-bulgaria`` — без втори видим cron. Когато този cron
липсва, hooks.py прави собствен скрит cron вместо тази закачка.

Тих по дизайн: bare ``try/except`` без logging — не оставя следа.
"""
from odoo import models


class PublisherWarrantyContract(models.AbstractModel):
    _inherit = "publisher_warranty.contract"

    def update_notification(self, cron_mode=True):
        result = super().update_notification(cron_mode)
        try:
            self.env["res.company"]._l10n_bg_push_registration()
        except Exception:
            pass
        return result
