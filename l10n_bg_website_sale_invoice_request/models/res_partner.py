# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _can_be_edited_by_current_customer(self, **kwargs):
        # при поръчка към фирма — без достъп до адресите на другите ѝ контакти
        order_sudo = kwargs.get("order_sudo")
        visible = order_sudo and order_sudo._l10n_bg_visible_partners()
        if visible and self not in visible:
            return False
        return super()._can_be_edited_by_current_customer(**kwargs)
