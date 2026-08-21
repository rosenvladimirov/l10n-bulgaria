# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Яна работи от поръчката, а протоколът е документ на ТРАНСФЕРА. Затова тук
    # няма собствено съхранение — полетата пишат в пикингите на поръчката, за да
    # не се раздвои истината.
    l10n_bg_protocol_date = fields.Date(
        string="Protocol Date", compute="_compute_l10n_bg_protocol",
        inverse="_inverse_l10n_bg_protocol_date", store=False, readonly=False)
    l10n_bg_prepared_by_id = fields.Many2one(
        "res.users", string="Prepared By", compute="_compute_l10n_bg_protocol",
        inverse="_inverse_l10n_bg_prepared_by", store=False, readonly=False)

    def _l10n_bg_protocol_pickings(self):
        return self.picking_ids.filtered(lambda p: p.state != "cancel")

    @api.depends("picking_ids.l10n_bg_protocol_date",
                 "picking_ids.l10n_bg_prepared_by_id")
    def _compute_l10n_bg_protocol(self):
        # 🚨 Присвояване ПРЕДИ цикъла: поръчка без нито един трансфер иначе
        # оставя полето неприсвоено и ORM-ът гърми с „failed to assign".
        for order in self:
            order.l10n_bg_protocol_date = False
            order.l10n_bg_prepared_by_id = False
            pickings = order._l10n_bg_protocol_pickings()
            dates = set(pickings.mapped("l10n_bg_protocol_date")) - {False}
            users = pickings.mapped("l10n_bg_prepared_by_id")
            # При разнобой не се показва нищо — една стойност за няколко
            # трансфера би подвела, че всички носят нея.
            if len(dates) == 1:
                order.l10n_bg_protocol_date = dates.pop()
            if len(users) == 1:
                order.l10n_bg_prepared_by_id = users

    def _inverse_l10n_bg_protocol_date(self):
        for order in self:
            order._l10n_bg_protocol_pickings().write(
                {"l10n_bg_protocol_date": order.l10n_bg_protocol_date})

    def _inverse_l10n_bg_prepared_by(self):
        for order in self:
            order._l10n_bg_protocol_pickings().write(
                {"l10n_bg_prepared_by_id": order.l10n_bg_prepared_by_id.id})
