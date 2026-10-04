# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_frontend_writable_fields(self):
        # ЕИК — фирма без ДДС регистрация има само него
        return super()._get_frontend_writable_fields() | {"l10n_bg_uic"}
