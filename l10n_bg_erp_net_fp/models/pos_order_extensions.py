"""
pos.order — proxy-aware extensions.

ADD-only — overrides `_add_mail_attachment` to allow sending the
receipt e-mail with no image attachment (the fiscal device already
produced the physical paper receipt; the e-mail is just a text
notification with order details + a link to the back-end record).
"""

from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _add_mail_attachment(self, name, ticket, basic_ticket):
        # Empty ticket → no image — frontend pattern when the order has
        # already been printed by an external fiscal device, so we just
        # send the text-only e-mail. Core would crash on
        # `attachment.create(datas="")` so we short-circuit instead.
        if not ticket and not basic_ticket:
            return [(6, 0, [])]
        return super()._add_mail_attachment(name, ticket, basic_ticket)
