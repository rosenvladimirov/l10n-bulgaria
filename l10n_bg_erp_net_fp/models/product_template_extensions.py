"""
product.template — PLU mapping fields for proxy-side PLU sync.

PLU# is a single Odoo-side number per product (assumed shared across
devices in the same company). Auto-assigned from `fiscal.plu_sequence`
on first sync; admins can set/override manually.

ADD-only — does NOT change existing product behaviour.
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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
    # Source of truth: Many2one to account.tax.group (unified with
    # l10n.bg.fiscal.plu.vat_group_id). Letter (А/Б/В/Г) is derived
    # from tax_group.l10n_bg_fiscal_tax_group via the computed below.
    l10n_bg_fiscal_vat_group_id = fields.Many2one(
        "account.tax.group",
        string="Fiscal VAT Group",
        index=True,
        help="Tax group programmed on the fiscal device for this product. "
        "The device letter (А/Б/В/Г) is derived from the tax group's "
        "`l10n_bg_fiscal_tax_group` field. Unified with "
        "`l10n.bg.fiscal.plu.vat_group_id` — set in either place and the "
        "other auto-updates.",
    )
    # Back-compat letter — computed from the M2O above. Kept as a field
    # because existing callers (proxy push, JS, search filters) expect
    # the letter directly ("А"/"Б"/"В"/"Г").
    l10n_bg_fiscal_vat_group = fields.Selection(
        DATECS_VAT_GROUPS,
        string="Fiscal VAT Letter",
        compute="_compute_l10n_bg_fiscal_vat_letter",
        store=True,
        readonly=True,
        help="Device letter (А/Б/В/Г) — derived from `Fiscal VAT Group`. "
        "Read-only since v0.13.7; set via the tax group instead.",
    )

    @api.depends("l10n_bg_fiscal_vat_group_id.l10n_bg_fiscal_tax_group")
    def _compute_l10n_bg_fiscal_vat_letter(self):
        for r in self:
            tg = r.l10n_bg_fiscal_vat_group_id
            r.l10n_bg_fiscal_vat_group = (
                tg.l10n_bg_fiscal_tax_group if tg else "А"
            )
    l10n_bg_fiscal_measurement_unit = fields.Selection(
        DATECS_MEASUREMENT_UNITS,
        string="Fiscal Measurement Unit",
        default="0",
        help="Measurement unit slot for the fiscal device PLU (Datecs "
        "PM syntax #2 field 15).",
    )
    # Слот-pressure управление за устройства с твърд лимит (BlueCash-50 = 3000).
    # Default True (opt-out) — повечето retail артикули с баркод са eligible.
    # False → продажбата минава през free-price fallback (Datecs cmd 0x31),
    # името + цената идват от Odoo в момента на продажбата, без слот на ФУ.
    l10n_bg_fiscal_plu_eligible = fields.Boolean(
        string="Eligible for PLU Slot",
        default=True,
        index=True,
        help="When True, this product gets allocated a PLU slot on the "
        "fiscal device and is pushed at the next Open Shift. When False, "
        "sales fall back to free-price entry (cmd 0x31) — the name and "
        "price travel per-receipt instead of being programmed once. "
        "Disable for long-tail items rarely sold so the limited PLU table "
        "(3000 slots on FP-class devices like BlueCash-50) stays for hot "
        "SKUs. Native BlueCash client (`BlueCash.PluClient`) reads this "
        "field to build the push set.",
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

    # ─── Mid-shift stale tracking ──────────────────────────────────
    # Watch the fields that flip a PLU's push_state to stale or
    # name_drift on the next consistency check. We don't auto-push to
    # the device mid-shift — mixing old + new prices in the same Z
    # cycle would scramble the fiscal log. The flag is for the next
    # session-open hook to pick up.
    _L10N_BG_PLU_WATCHED_FIELDS = ("name", "list_price")

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in self._L10N_BG_PLU_WATCHED_FIELDS):
            self._l10n_bg_revalidate_linked_plus()
        return res

    def _l10n_bg_revalidate_linked_plus(self):
        """Re-run consistency check on every PLU whose linked products
        belong to one of these templates. Quietly no-ops if no PLUs
        link to the changed templates — most product writes will hit
        this path. Errors are logged, not raised — a stale PLU is
        better than a failed product.write."""
        try:
            Plu = self.env["l10n.bg.fiscal.plu"]
            product_ids = self.product_variant_ids.ids
            if not product_ids:
                return
            plus = Plu.search([("product_ids", "in", product_ids)])
            for plu in plus:
                plu._check_consistency()
        except Exception:  # noqa: BLE001
            _logger.exception(
                "Mid-shift PLU revalidation failed for templates %s — "
                "continuing without flipping push_state.", self.ids,
            )

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


# ──────────────────────────────────────────────────────────────────
# POS data — изпращаме фискалните полета на product.product, за да може
# JS-ът (erp_net_fp_printer.js) да чете `l10n_bg_fiscal_plu_number` и да
# изпраща `pluNumber` в item-ите на фискалния бон (за PLU-only устройства).
# ──────────────────────────────────────────────────────────────────


class ProductProduct(models.Model):
    _inherit = "product.product"

    # Related fields от template-а — за да са достъпни на product.product
    # records (POS frontend ползва product.product, не product.template).
    l10n_bg_fiscal_plu_number = fields.Integer(
        related="product_tmpl_id.l10n_bg_fiscal_plu_number",
        store=True, readonly=True, index=True,
    )
    l10n_bg_fiscal_vat_group = fields.Selection(
        related="product_tmpl_id.l10n_bg_fiscal_vat_group",
        store=False, readonly=True,
    )
    l10n_bg_fiscal_measurement_unit = fields.Selection(
        related="product_tmpl_id.l10n_bg_fiscal_measurement_unit",
        store=False, readonly=True,
    )
    l10n_bg_fiscal_plu_eligible = fields.Boolean(
        related="product_tmpl_id.l10n_bg_fiscal_plu_eligible",
        store=True, readonly=True, index=True,
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        for f in ("l10n_bg_fiscal_plu_number", "l10n_bg_fiscal_vat_group",
                  "l10n_bg_fiscal_measurement_unit",
                  "l10n_bg_fiscal_plu_eligible"):
            if f not in fields_list and f in self._fields:
                fields_list.append(f)
        return fields_list
