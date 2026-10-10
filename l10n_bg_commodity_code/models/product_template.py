# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""Кодът по КН на шаблона — изглед към вариантите.

* ``l10n_bg_commodity_code`` на шаблона: при един вариант — кодът на
  варианта; при няколко — общият код, ако е еднакъв, иначе празно.
  Запис на шаблона (inverse) пише кода във ВСИЧКИ варианти.
* ``hs_code`` (ядро, stock_delivery) носи КН8: общия за вариантите или
  празно. Поддържа се явно:
    - запис на варианта → ``_l10n_bg_sync_hs_code`` обновява шаблона;
    - ръчен запис на ``hs_code`` (стар път, импорт) → попълва източника
      на вариантите, които още нямат код (съществуващ код не се
      презаписва).
"""
from odoo import api, fields, models

from .commodity_code_utils import digits_candidate, normalize_commodity_code
from .product_product import COMMODITY_STATES

# Контекст за записа на hs_code от синхрона — за да не тръгне обратният път.
_SYNC_CTX = "l10n_bg_commodity_hs_sync"

# Поредност на „най-лошото“ състояние, когато вариантите се различават.
_STATE_PRIORITY = ["invalid_format", "not_in_nomenclature", "missing", "ok", "service"]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_bg_commodity_code = fields.Char(
        string="Commodity Code (CN/TARIC)",
        compute="_compute_l10n_bg_commodity_code",
        inverse="_inverse_l10n_bg_commodity_code",
        store=True,
        help="TARIC10 when known, otherwise CN8; digits only. With a single "
             "variant this is the variant's code. With several variants it "
             "shows the common code (empty when the variants differ); "
             "setting it here writes the code to ALL variants.",
    )
    l10n_bg_cn8 = fields.Char(
        string="CN8 Code",
        compute="_compute_l10n_bg_commodity_levels",
    )
    l10n_bg_hs6 = fields.Char(
        string="HS6 Code",
        compute="_compute_l10n_bg_commodity_levels",
    )
    l10n_bg_taric10 = fields.Char(
        string="TARIC10 Code",
        compute="_compute_l10n_bg_commodity_levels",
    )
    l10n_bg_commodity_state = fields.Selection(
        selection=COMMODITY_STATES,
        string="Commodity Code Status",
        compute="_compute_l10n_bg_commodity_levels",
        search="_search_l10n_bg_commodity_state",
    )

    # ------------------------------------------------------------------
    @api.depends("product_variant_ids.l10n_bg_commodity_code")
    def _compute_l10n_bg_commodity_code(self):
        for template in self:
            codes = set(template.product_variant_ids.mapped("l10n_bg_commodity_code"))
            template.l10n_bg_commodity_code = codes.pop() if len(codes) == 1 else False

    def _inverse_l10n_bg_commodity_code(self):
        for template in self:
            variants = template.product_variant_ids
            code = normalize_commodity_code(template.l10n_bg_commodity_code)
            if not code and len(set(variants.mapped("l10n_bg_commodity_code"))) > 1:
                # Празното на шаблона значи „вариантите се различават“, не
                # „изтрий“: кръгов експорт/импорт на шаблона би изтрил кодовете
                # на всички варианти. Общ код се чисти нормално.
                continue
            to_write = variants.filtered(lambda v: v.l10n_bg_commodity_code != code)
            if to_write:
                to_write.write({"l10n_bg_commodity_code": code})

    @api.depends(
        "product_variant_ids.l10n_bg_cn8",
        "product_variant_ids.l10n_bg_hs6",
        "product_variant_ids.l10n_bg_taric10",
        "product_variant_ids.l10n_bg_commodity_code",
        "type",
    )
    @api.depends_context("date")
    def _compute_l10n_bg_commodity_levels(self):
        for template in self:
            variants = template.product_variant_ids
            for fname in ("l10n_bg_cn8", "l10n_bg_hs6", "l10n_bg_taric10"):
                values = set(variants.mapped(fname))
                template[fname] = values.pop() if len(values) == 1 else False
            states = set(variants.mapped("l10n_bg_commodity_state"))
            if not states:
                template.l10n_bg_commodity_state = (
                    "service" if template.type == "service" else "missing"
                )
            else:
                template.l10n_bg_commodity_state = next(
                    s for s in _STATE_PRIORITY if s in states
                )

    @api.model
    def _search_l10n_bg_commodity_state(self, operator, value):
        return [("product_variant_ids.l10n_bg_commodity_state", operator, value)]

    def _get_related_fields_variant_template(self):
        # При създаване на шаблон стойността от vals стига до първия вариант
        return super()._get_related_fields_variant_template() + [
            "l10n_bg_commodity_code",
        ]

    # ------------------------------------------------------------------
    # hs_code ⇄ кодът на вариантите
    # ------------------------------------------------------------------
    def _l10n_bg_sync_hs_code(self):
        """hs_code = общият КН8 на активните варианти или празно."""
        for template in self.exists():
            variants = template.product_variant_ids
            cn8s = set(variants.mapped("l10n_bg_cn8")) if variants else set()
            if not any(cn8s) and not digits_candidate(template.hs_code):
                # Никой вариант няма код, а hs_code е заварена стойност,
                # която не прилича на КН8/TARIC10 — не я трием мълчаливо.
                continue
            common = cn8s.pop() if len(cn8s) == 1 else False
            if (template.hs_code or False) != (common or False):
                template.with_context(**{_SYNC_CTX: True}).write({"hs_code": common})

    def _l10n_bg_propagate_hs_code(self, value):
        """Ръчно въведен hs_code → източник на вариантите без код.

        Взема се само стойност с 8 или 10 цифри (след махане на
        разделителите); съществуващ код на вариант не се презаписва.
        """
        candidate = digits_candidate(value)
        if not candidate:
            return
        for template in self:
            empty = template.product_variant_ids.filtered(
                lambda v: not v.l10n_bg_commodity_code
            )
            if empty:
                empty.write({"l10n_bg_commodity_code": candidate})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "l10n_bg_commodity_code" in vals:
                vals["l10n_bg_commodity_code"] = normalize_commodity_code(
                    vals["l10n_bg_commodity_code"]
                )
        templates = super().create(vals_list)
        if not self.env.context.get(_SYNC_CTX):
            for template, vals in zip(templates, vals_list):
                if vals.get("hs_code") and not vals.get("l10n_bg_commodity_code"):
                    template._l10n_bg_propagate_hs_code(vals["hs_code"])
        return templates

    def write(self, vals):
        if "l10n_bg_commodity_code" in vals:
            vals["l10n_bg_commodity_code"] = normalize_commodity_code(
                vals["l10n_bg_commodity_code"]
            )
        res = super().write(vals)
        if (
            "hs_code" in vals
            and "l10n_bg_commodity_code" not in vals
            and not self.env.context.get(_SYNC_CTX)
        ):
            self._l10n_bg_propagate_hs_code(vals["hs_code"])
        return res
