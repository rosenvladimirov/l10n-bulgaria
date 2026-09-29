# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models
from odoo.tools import urls

PAY_ROUTE = "/l10n_bg_telegram/pay"


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_bg_telegram_user_id = fields.Many2one(
        "l10n.bg.telegram.user",
        string="Telegram User",
        readonly=True,
        copy=False,
        index="btree_not_null",
    )

    def _l10n_bg_telegram_pay_url(self):
        """Линкът от бота към плащането в магазина (носи access_token на поръчката)."""
        self.ensure_one()
        base = (self.website_id or self.env["website"]).get_base_url()
        token = self._portal_ensure_token()
        return urls.urljoin(base, f"{PAY_ROUTE}/{self.id}/{token}")
