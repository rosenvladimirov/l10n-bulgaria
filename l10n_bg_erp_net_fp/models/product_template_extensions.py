"""
product.template — PLU mapping fields for proxy-side PLU sync.

PLU# is a single Odoo-side number per product (assumed shared across
devices in the same company). Auto-assigned from `fiscal.plu_sequence`
on first sync; admins can set/override manually.

ADD-only — does NOT change existing product behaviour.
"""

from odoo import api, fields, models


# Datecs PM v2.11.4 measurement unit slots (PDF §4.55.1 syntax #2).
# Slots 0..4 are device defaults; 5..19 are configurable via the
# `Unit_name` parameter (cmd 0xFF).
DATECS_MEASUREMENT_UNITS = [
    ("0", "бр."),
    ("1", "кг"),
    ("2", "м"),
    ("3", "л"),
    ("4", "ч"),
]

# 8 VAT slots А..З Cyrillic (Latin equivalents A..H also accepted on
# vendor-firmware level). Maps to `valVat[0..7]` parameter index.
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

    l10n_bg_fiscal_plu_number = fields.Integer(
        string="Fiscal PLU #",
        copy=False,
        index=True,
        help="PLU number on the fiscal device (1..100000 capable, "
        "1..3000 basic). Auto-assigned on first sync; can be overridden "
        "manually.",
    )
    l10n_bg_fiscal_vat_group = fields.Selection(
        DATECS_VAT_GROUPS,
        string="Fiscal VAT Group",
        default="А",
        help="VAT group letter on the fiscal device. Maps to "
        "device's valVat parameter index — must agree with the "
        "device's actual VAT-rate programming.",
    )
    l10n_bg_fiscal_measurement_unit = fields.Selection(
        DATECS_MEASUREMENT_UNITS,
        string="Fiscal Measurement Unit",
        default="0",
        help="Measurement unit slot for the fiscal device PLU (Datecs "
        "PM syntax #2 field 15).",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Auto-assign PLU# on create if not provided. Existing products
        # without a PLU keep nothing (admin assigns later via wizard).
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("l10n_bg_fiscal_plu_number"):
                next_num = seq.next_by_code("fiscal.plu_sequence")
                if next_num:
                    try:
                        vals["l10n_bg_fiscal_plu_number"] = int(next_num)
                    except (ValueError, TypeError):
                        pass
        return super().create(vals_list)

    def _l10n_bg_fiscal_assign_plu(self):
        """Bulk-assign PLU# to records that don't have one. Called by
        sync wizards; safe to invoke as no-op if all already have PLUs.
        """
        seq = self.env["ir.sequence"]
        for tmpl in self.filtered(lambda t: not t.l10n_bg_fiscal_plu_number):
            next_num = seq.next_by_code("fiscal.plu_sequence")
            if next_num:
                try:
                    tmpl.l10n_bg_fiscal_plu_number = int(next_num)
                except (ValueError, TypeError):
                    pass
