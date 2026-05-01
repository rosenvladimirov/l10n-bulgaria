"""
account.tax.group — map BG VAT groups to Datecs PM device VAT slots.

Datecs PM v2.11.4 (PDF §4.55.1) supports 8 VAT slots labelled А..З
(Cyrillic) or A..H (Latin), corresponding to `valVat[0..7]` parameter
indexes (cmd 0xFF). Bulgarian fiscal practice typically uses:
  А = 20% standard,  Б = 9% reduced,  В = 0%/exempt,  Г = ...

The exact mapping is per device — Rosen's BG-installed devices ship
with А=20%/Б=9%/В=0%/Г=20% (matches sibling l10n_bg_erp_net_fp).
This Selection lets each tax group pick its slot; the JS frontend
reads it via `_load_pos_data_fields` to choose TaxGr in cmd 0x6B
(PLU programming) and cmd 0x31 (sale registration).
"""

from odoo import api, fields, models


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_bg_fp_datecs_tax_group = fields.Selection(
        [
            ("А", "А"),
            ("Б", "Б"),
            ("В", "В"),
            ("Г", "Г"),
            ("Д", "Д"),
            ("Е", "Е"),
            ("Ж", "Ж"),
            ("З", "З"),
        ],
        string="Datecs PM VAT slot",
        help="Maps this tax group to one of the 8 VAT slots on the "
        "Datecs PM device (А..З = valVat[0..7] in cmd 0xFF). The "
        "exact rate-to-slot assignment is set on the device via cmd "
        "0x53 (VAT programming).",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == "BG":
            return res + ["l10n_bg_fp_datecs_tax_group"]
        return res
