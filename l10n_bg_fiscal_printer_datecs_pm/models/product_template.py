"""
product.template — Datecs PM PLU mapping fields.

PLU# is a single Odoo-side number per product (assumed shared across
devices in the same company — multi-device-with-distinct-PLU-tables is
out of scope for v18.0.1.0.0; add a per-device mapping table later if
needed).

Auto-assigned from `l10n_bg_fp_datecs.plu_sequence` the first time the
product is sync'd to a device; admins can set/override manually.
"""

from odoo import api, fields, models


# PDF §4.55.1 syntax #2 measurement_unit values (0..19). Indexes 5..19
# are device-programmable custom unit names — we expose only the four
# documented defaults; admins set the device-side custom slots through
# Unit_name parameter (cmd 0xFF) if they want richer choices.
DATECS_MEASUREMENT_UNITS = [
    ("0", "бр."),
    ("1", "кг"),
    ("2", "м"),
    ("3", "л"),
    ("4", "ч"),
]

# PDF §4.55.1 TaxGr range. Datecs supports 8 VAT slots (А..З Cyrillic
# or A..H Latin). For BG fiscal devices the Cyrillic labels are
# canonical; map letters to the device's `valVat` parameter indexes
# 0..7 (cmd 0xFF).
DATECS_VAT_GROUPS = [
    ("А", "А (стандартна 20%)"),
    ("Б", "Б (намалена 9%)"),
    ("В", "В"),
    ("Г", "Г"),
    ("Д", "Д"),
    ("Е", "Е"),
    ("Ж", "Ж"),
    ("З", "З (нулева)"),
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_bg_fp_datecs_plu_number = fields.Integer(
        string="Datecs PLU #",
        copy=False,
        index=True,
        help="PLU number on the fiscal device (1..100000 capable, "
        "1..3000 basic). Auto-assigned on first sync; can be overridden "
        "manually.",
    )
    l10n_bg_fp_datecs_vat_group = fields.Selection(
        DATECS_VAT_GROUPS,
        string="Datecs VAT Group",
        default="А",
        help="VAT group letter on the fiscal device. Maps to the "
        "device's `valVat` parameter index (cmd 0xFF) — must agree "
        "with the device's actual VAT-rate programming (cmd 0x53).",
    )
    l10n_bg_fp_datecs_measurement_unit = fields.Selection(
        DATECS_MEASUREMENT_UNITS,
        string="Datecs Measurement Unit",
        default="0",
        help="Measurement unit slot on the fiscal device (PLU syntax #2 "
        "field 15). Slots 0..4 are device defaults; slots 5..19 are "
        "configurable via the `Unit_name` parameter.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Auto-assign PLU# on create if not provided. Sequencing is
        # idempotent: if a product was given an explicit PLU# (manual
        # override) we keep it; otherwise we draw the next number.
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("l10n_bg_fp_datecs_plu_number"):
                next_num = seq.next_by_code("l10n_bg_fp_datecs.plu_sequence")
                if next_num:
                    vals["l10n_bg_fp_datecs_plu_number"] = int(next_num)
        return super().create(vals_list)

    def _l10n_bg_fp_datecs_assign_plu_number(self):
        """Assign a PLU# to records that don't have one. Called on demand
        by `device.action_sync_plu` for templates created before the
        module was installed (no auto-assign at create time).
        """
        seq = self.env["ir.sequence"]
        for tmpl in self.filtered(lambda t: not t.l10n_bg_fp_datecs_plu_number):
            next_num = seq.next_by_code("l10n_bg_fp_datecs.plu_sequence")
            if next_num:
                tmpl.l10n_bg_fp_datecs_plu_number = int(next_num)
