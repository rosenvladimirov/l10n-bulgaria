# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""Кодът по КН живее на варианта (решение на Росен, 10.10.2026).

Едно поле-източник ``l10n_bg_commodity_code``: TARIC10, когато е известен
(митническа декларация при внос от трети страни), иначе КН8. От него се
изчисляват КН8, HS6 и TARIC10. Ядреното ``hs_code`` на шаблона носи КН8 —
общия за вариантите или празно (поддържа се от ``_l10n_bg_sync_hs_code``).

Всички потребители (SAF-T, Интрастат, СВФР, митнически ставки) четат
кода през помощните методи по-долу, не през суровото ``hs_code``.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain

from .commodity_code_utils import (
    SAFT_NOT_APPLICABLE_CODE,
    SAFT_SERVICE_CODE,
    is_valid_commodity_code,
    normalize_commodity_code,
    split_commodity_code,
)

COMMODITY_STATES = [
    ("ok", "OK"),
    ("missing", "Missing"),
    ("invalid_format", "Invalid format"),
    ("not_in_nomenclature", "Not in nomenclature"),
    ("service", "Service"),
]


class ProductProduct(models.Model):
    _inherit = "product.product"

    l10n_bg_commodity_code = fields.Char(
        string="Commodity Code (CN/TARIC)",
        index=True,
        help="Source of truth for the product's commodity code: the "
             "10-digit TARIC code when known (e.g. from an import customs "
             "declaration), otherwise the 8-digit Combined Nomenclature "
             "(CN8) code. Digits only. HS6, CN8 and TARIC10 are derived "
             "from it.",
    )
    l10n_bg_cn8 = fields.Char(
        string="CN8 Code",
        compute="_compute_l10n_bg_commodity_levels",
        store=True,
        index=True,
        help="Combined Nomenclature code (first 8 digits). Used for SAF-T "
             "and Intrastat.",
    )
    l10n_bg_hs6 = fields.Char(
        string="HS6 Code",
        compute="_compute_l10n_bg_commodity_levels",
        store=True,
        help="Harmonized System code (first 6 digits). Used on courier "
             "and shipping documents.",
    )
    l10n_bg_taric10 = fields.Char(
        string="TARIC10 Code",
        compute="_compute_l10n_bg_commodity_levels",
        store=True,
        help="Integrated EU tariff code (10 digits). Filled only when the "
             "commodity code itself has 10 digits — never padded with "
             "zeros.",
    )
    l10n_bg_cn_code_id = fields.Many2one(
        comodel_name="l10n.bg.cn.code",
        string="CN Nomenclature Entry",
        compute="_compute_l10n_bg_cn_code_id",
        help="Entry of the CN8 code in the nomenclature of the current "
             "year, if the nomenclature for the year is loaded.",
    )
    l10n_bg_commodity_state = fields.Selection(
        selection=COMMODITY_STATES,
        string="Commodity Code Status",
        compute="_compute_l10n_bg_commodity_state",
        search="_search_l10n_bg_commodity_state",
        help="OK: valid code (and present in the nomenclature of the "
             "current year when that nomenclature is loaded).\n"
             "Missing: goods without a commodity code.\n"
             "Invalid format: the code is not 8 or 10 digits.\n"
             "Not in nomenclature: the CN8 code does not exist in the "
             "nomenclature of the current year.\n"
             "Service: services need no code (SAF-T uses 00000000).",
    )

    # ------------------------------------------------------------------
    # Изчисления
    # ------------------------------------------------------------------
    @api.depends("l10n_bg_commodity_code")
    def _compute_l10n_bg_commodity_levels(self):
        for product in self:
            cn8, hs6, taric10 = split_commodity_code(
                product.l10n_bg_commodity_code
            )
            product.l10n_bg_cn8 = cn8 or False
            product.l10n_bg_hs6 = hs6 or False
            product.l10n_bg_taric10 = taric10 or False

    @api.depends("l10n_bg_cn8")
    @api.depends_context("date")
    def _compute_l10n_bg_cn_code_id(self):
        year = self._l10n_bg_year()
        cn8s = [c for c in self.mapped("l10n_bg_cn8") if c]
        entries = {}
        if cn8s:
            for entry in self.env["l10n.bg.cn.code"].search([
                ("year", "=", year), ("code", "in", cn8s),
            ]):
                entries[entry.code] = entry
        for product in self:
            product.l10n_bg_cn_code_id = entries.get(product.l10n_bg_cn8, False)

    @api.depends("l10n_bg_commodity_code", "type")
    @api.depends_context("date")
    def _compute_l10n_bg_commodity_state(self):
        year = self._l10n_bg_year()
        for product in self:
            product.l10n_bg_commodity_state = product._l10n_bg_commodity_state_for_year(year)

    def _l10n_bg_commodity_state_for_year(self, year):
        """Състоянието на кода спрямо КН за дадена година."""
        self.ensure_one()
        if self.type == "service":
            return "service"
        code = self.l10n_bg_commodity_code
        if not code:
            return "missing"
        if not is_valid_commodity_code(code):
            return "invalid_format"
        if not self.env["l10n.bg.cn.code"]._l10n_bg_is_known(code[:8], year):
            return "not_in_nomenclature"
        return "ok"

    @api.model
    def _l10n_bg_year(self, date=None):
        """Годината на справочника: от аргумента, от контекста или днес."""
        date = date or self.env.context.get("date")
        if date:
            return fields.Date.to_date(date).year
        return fields.Date.context_today(self).year

    @api.model
    def _search_l10n_bg_commodity_state(self, operator, value):
        """Търсене по състоянието (за филтрите „Липсващ“/„Невалиден“ код).

        Състоянието зависи от справочника на текущата година, затова не е
        stored — домейнът се строи от stored полетата и от кодовете на годината.
        """
        if operator in ("=", "!="):
            values = [value] if value else []
            negate = operator == "!="
        elif operator in ("in", "not in"):
            values = list(value or [])
            negate = operator == "not in"
        else:
            return NotImplemented
        year = self._l10n_bg_year()
        codes = self.env["l10n.bg.cn.code"]._l10n_bg_codes_for_year(year)
        goods = [("type", "!=", "service")]
        per_state = {
            "service": [("type", "=", "service")],
            "missing": goods + [("l10n_bg_commodity_code", "=", False)],
            "invalid_format": goods + [
                ("l10n_bg_commodity_code", "!=", False),
                ("l10n_bg_cn8", "=", False),
            ],
            "not_in_nomenclature": (
                goods + [
                    ("l10n_bg_cn8", "!=", False),
                    ("l10n_bg_cn8", "not in", list(codes)),
                ] if codes else Domain.FALSE
            ),
            "ok": goods + [("l10n_bg_cn8", "!=", False)] + (
                [("l10n_bg_cn8", "in", list(codes))] if codes else []
            ),
        }
        domain = Domain.OR(
            Domain(per_state[v]) for v in values if v in per_state
        )
        return ~domain if negate else domain

    # ------------------------------------------------------------------
    # Ограничения и нормализация
    # ------------------------------------------------------------------
    @api.constrains("l10n_bg_commodity_code")
    def _check_l10n_bg_commodity_code(self):
        for product in self:
            code = product.l10n_bg_commodity_code
            if code and not is_valid_commodity_code(code):
                raise ValidationError(_(
                    "The commodity code '%(code)s' of product '%(product)s' "
                    "must contain only digits and be exactly 8 (CN8) or "
                    "10 (TARIC10) digits long.",
                    code=code,
                    product=product.display_name,
                ))

    @api.model
    def _l10n_bg_normalize_vals(self, vals):
        if "l10n_bg_commodity_code" in vals:
            vals["l10n_bg_commodity_code"] = normalize_commodity_code(
                vals["l10n_bg_commodity_code"]
            )
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._l10n_bg_normalize_vals(vals)
            self._l10n_bg_inherit_sibling_code(vals)
        products = super().create(vals_list)
        # Синхрон само когато има смисъл: създаден вариант с код или шаблон,
        # който вече има няколко варианта. Първият (празен) вариант на нов
        # шаблон НЕ трие заварения hs_code на шаблона.
        templates = products.filtered(
            lambda p: p.l10n_bg_commodity_code
            or len(p.product_tmpl_id.product_variant_ids) > 1
        ).product_tmpl_id
        templates._l10n_bg_sync_hs_code()
        # Вариант, създаден директно с hs_code (импорт на product.product):
        # шаблонът се ражда преди варианта, затова попълваме източника тук.
        for product, vals in zip(products, vals_list):
            if vals.get("hs_code") and not product.l10n_bg_commodity_code:
                product.product_tmpl_id._l10n_bg_propagate_hs_code(vals["hs_code"])
        return products

    @api.model
    def _l10n_bg_inherit_sibling_code(self, vals):
        """Нов вариант (добавена стойност на атрибут) наследява общия код.

        Само ако всички активни събратя в шаблона са с един и същ непразен
        код; при различни кодове или без събратя — нищо.
        """
        if "l10n_bg_commodity_code" in vals or not vals.get("product_tmpl_id"):
            return vals
        siblings = self.env["product.template"].browse(
            vals["product_tmpl_id"]).product_variant_ids
        codes = set(siblings.mapped("l10n_bg_commodity_code"))
        if len(codes) == 1:
            code = codes.pop()
            if code:
                vals["l10n_bg_commodity_code"] = code
        return vals

    def write(self, vals):
        self._l10n_bg_normalize_vals(vals)
        old_templates = self.product_tmpl_id if "product_tmpl_id" in vals else False
        res = super().write(vals)
        if {"l10n_bg_commodity_code", "active", "product_tmpl_id"} & set(vals):
            templates = self.product_tmpl_id
            if old_templates:
                templates |= old_templates
            templates._l10n_bg_sync_hs_code()
        return res

    def unlink(self):
        templates = self.product_tmpl_id
        res = super().unlink()
        templates.exists()._l10n_bg_sync_hs_code()
        return res

    # ------------------------------------------------------------------
    # Помощни методи за потребителите (SAF-T, Интрастат, СВФР, мита)
    # ------------------------------------------------------------------
    def _l10n_bg_cn8(self, date=None):
        """Валидният КН8 на варианта или ''.

        Без дата — проверява се само форматът. С дата — КН8 трябва да
        съществува в КН за годината на датата; ако справочникът за тази
        година не е зареден, форматът решава.
        """
        self.ensure_one()
        cn8 = self.l10n_bg_cn8 or ""
        if not cn8 or date is None:
            return cn8
        year = self._l10n_bg_year(date)
        if not self.env["l10n.bg.cn.code"]._l10n_bg_is_known(cn8, year):
            return ""
        return cn8

    def _l10n_bg_saft_commodity_code(self, date=None):
        """Кодът за ProductCommodityCode / StockAccountCommodityCode в SAF-T.

        Услуга → 00000000; стока с КН8, валиден за годината на периода
        (или с валиден формат при незареден справочник) → КН8; иначе → 0
        (като в еталонния Odoo EE l10n_bg_saft). Стоките с 0 се отчитат
        отделно като предупреждение в отчета.
        """
        self.ensure_one()
        if self.type == "service":
            return SAFT_SERVICE_CODE
        return self._l10n_bg_cn8(date) or SAFT_NOT_APPLICABLE_CODE

    def _l10n_bg_commodity_issues(self, date=None):
        """Списък с причини, поради които кодът не става за отчитане."""
        self.ensure_one()
        year = self._l10n_bg_year(date)
        state = self._l10n_bg_commodity_state_for_year(year)
        if state == "missing":
            return [_("No commodity code (CN8/TARIC10) is set.")]
        if state == "invalid_format":
            return [_(
                "The commodity code '%s' must contain only digits and be "
                "8 or 10 digits long.",
                self.l10n_bg_commodity_code,
            )]
        if state == "not_in_nomenclature":
            return [_(
                "The CN8 code %(code)s does not exist in the Combined "
                "Nomenclature for %(year)s.",
                code=self.l10n_bg_cn8,
                year=year,
            )]
        return []
