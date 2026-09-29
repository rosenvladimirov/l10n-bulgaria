# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # Записът на доставчика е noupdate ⇒ новото поле от data/ не стига до вече
    # инсталираните бази. Без формата ядрото не пренасочва към myPOS изобщо.
    env = api.Environment(cr, SUPERUSER_ID, {})
    view = env.ref("payment_mypos.redirect_form", raise_if_not_found=False)
    if not view:
        return
    providers = env["payment.provider"].search(
        [("code", "=", "mypos"), ("redirect_form_view_id", "=", False)]
    )
    providers.redirect_form_view_id = view
