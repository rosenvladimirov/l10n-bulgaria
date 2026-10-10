# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models

# Мостът: издателят при печат (print.signer.mixin) и скриването на
# l10n_bg_* полетата в небългарска фирма — само там, където има модула.


class SaleOrder(models.Model):
    _inherit = ["sale.order", "l10n.bg.config.mixin", "print.signer.mixin"]
    _name = "sale.order"
