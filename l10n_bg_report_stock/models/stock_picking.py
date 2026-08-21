# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # 🔑 Датата на ПРОТОКОЛА не е датата на движението. Протоколът се подписва
    # тогава, когато страните се срещнат — понякога след, понякога преди
    # приключването на трансфера. Досега печатът вземаше `date_done`, а при
    # неприключен — `scheduled_date`, и нямаше как да се коригира.
    l10n_bg_protocol_date = fields.Date(
        string="Protocol Date",
        help="Date printed on the acceptance protocol. Leave empty to use the "
             "transfer date (effective date when done, scheduled date otherwise).",
        copy=False,
    )
    l10n_bg_prepared_by_id = fields.Many2one(
        "res.users",
        string="Prepared By",
        help="Person who drew up the acceptance protocol.",
        copy=False,
    )

    def _l10n_bg_protocol_date(self):
        """Датата за печат: ръчната, ако е сложена, иначе тази на трансфера."""
        self.ensure_one()
        if self.l10n_bg_protocol_date:
            return self.l10n_bg_protocol_date
        return self.date_done if self.state == "done" else self.scheduled_date
